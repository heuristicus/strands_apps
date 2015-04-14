#! /usr/bin/env python

import rospy
import actionlib
from actionlib_msgs.msg import GoalStatusArray, GoalStatus
from move_base_msgs.msg import MoveBaseAction
from door_pass.door_utils import DoorUtils    
   
class DoorPass(object):
    def __init__(self):
        max_trans_vel=rospy.get_param("~/max_trans_vel", 0.15)
        max_rot_vel=rospy.get_param("~/max_rot_vel", 0.4)
        base_radius=rospy.get_param("~/base_radius", 0.31)
        getting_further_counter_threshold=rospy.get_param("~/getting_further_counter_threshold", 5)
        distance_to_success=rospy.get_param("~/distance_to_success", 0.2)
        self.door_utils=DoorUtils(max_trans_vel=max_trans_vel,
                                  max_rot_vel=max_rot_vel,
                                  base_radius=base_radius,
                                  getting_further_counter_threshold=getting_further_counter_threshold,
                                  distance_to_success=distance_to_success)
        
        self.door_as=actionlib.SimpleActionServer('doorPassing', MoveBaseAction, execute_cb = self.execute_cb, auto_start=False) 
        self.door_as.start()
        
        self.mon_nav_status_sub=rospy.Subscriber("/monitored_navigation/status", GoalStatusArray, self.mon_nav_status_cb)
        self.mon_nav_executing=False

    def mon_nav_status_cb(self, data):
        result=False
        for goal in data.status_list:
            if goal.status==GoalStatus.ACTIVE:
                result=True
                break
        self.mon_nav_executing=result

    def execute_cb(self, goal):
        max_trans_vel=rospy.get_param("~/max_trans_vel", 0.15)
        max_rot_vel=rospy.get_param("~/max_rot_vel", 0.4)
        base_radius=rospy.get_param("~/base_radius", 0.31)
        getting_further_counter_threshold=rospy.get_param("~/getting_further_counter_threshold", 5)
        distance_to_success=rospy.get_param("~/distance_to_success", 0.2)        
        self.door_utils.set_params(max_trans_vel=max_trans_vel,
                                  max_rot_vel=max_rot_vel,
                                  base_radius=base_radius,
                                  getting_further_counter_threshold=getting_further_counter_threshold,
                                  distance_to_success=distance_to_success)
        
        if self.door_as.is_preempt_requested():
            self.door_as.set_preempted()
            return
        target_pose=goal.target_pose.pose
        rospy.loginfo("Door pass action server calling rotate towards pose")
        self.door_utils.rotate_towards_pose(target_pose)
        if self.door_as.is_preempt_requested():
            self.door_as.set_preempted()
            rospy.loginfo("Door pass action preempted")
            return
        rospy.loginfo("Door pass action server calling check door")
        door_open=self.door_utils.check_door(target_pose)
        if door_open:
            if self.door_as.is_preempt_requested():
                self.door_as.set_preempted()
                rospy.loginfo("Door pass action preempted")
                return
            rospy.loginfo("The door is open. Door pass action server is calling pass door")
            success=self.door_utils.pass_door(target_pose)
            if success:
                self.door_as.set_succeeded()
                return
            else:
                self.door_as.set_aborted()
                return
        else:
            rospy.loginfo("Door is closed. Disabling monitored navigation recoveries.")
            current_mon_nav_recover_states=rospy.get_param("/monitored_navigation/recover_states/", {})
            for mon_nav_recover_state in current_mon_nav_recover_states:
                rospy.set_param("/monitored_navigation/recover_states/" + mon_nav_recover_state, [False,0])
            self.door_as.set_aborted()
            #wait for mon nav to output failure and get recover states back on
            timeout=0
            while self.mon_nav_executing and not self.door_as.is_preempt_requested() and timeout<30:
                rospy.loginfo("Waiting for monitored navigation to stop executing")
                rospy.sleep(0.1)
                timeout=timeout+1
            rospy.loginfo("Monitored navigation stopped executing. Resetting monitored navigation recoveries.")
            rospy.set_param("/monitored_navigation/recover_states/", current_mon_nav_recover_states)
            return

    def main(self):
        rospy.spin()
    
if __name__ == '__main__':
    rospy.init_node("door_pass_node")
    passer=DoorPass()
    passer.main()
    
        
    
    
    
    

