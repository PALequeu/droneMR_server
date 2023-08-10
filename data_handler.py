import json
from hungarian_algorithm import HungarianAlgorithm
import math
from drone import Drone
from target import Target
from tkInterface import TkInterface

# Import the required libraries
from tkinter import *
from tkinter import ttk
import queue


class DataHandler:
    def __init__(self):
        self.ha = HungarianAlgorithm()
        self.number_of_slaves = 0
        self.leader_drone = None
        self.slave_drones = {}
        self.drone_order = []
        self.targets = [Target(1,0.2,0.5), Target(2,0.8,0.5)]
        self.position_queue = queue.Queue()
        #self.interface = TkInterface(self.position_queue)

        


    def process_data(self, data):
        parsed_data = self.parse_data(data)
        drone_info = parsed_data["droneInformation"]
        message_type = drone_info["messageType"]

        if message_type == "position":
            return self.process_position(parsed_data)

        elif message_type == "detection":
            return self.process_detection(parsed_data)

        elif message_type == "init":
            return self.process_init(parsed_data)
        

    def process_position(self, data):
        drone_info = data["droneInformation"]
        identification = drone_info["identification"]
        position = drone_info["position"]


        # check if drone is leader drone
        if self.leader_drone != None and identification["source"] == self.leader_drone.name:
            # update drone's position
            
            self.leader_drone.position = position
            print(self.leader_drone.name + " position updated")
            
            #self.interface.update_drone(self.leader_drone)

            for drone in self.slave_drones :
                self.slave_drones[drone].directives["headingDirective"] = self.get_heading_directive(drone)
    
            return {"success": True, "message": "drone position updated"}

        # else check if drone is slave drone
        
        elif identification["source"] in self.slave_drones:
            # update drone's position
            self.slave_drones[identification["source"]].position = position

            #self.interface.update_drone(self.slave_drones[identification["source"]])

            print(identification["source"] + " position update") 
            return {"success": True, "message": "drone position updated"}

        # else drone is not initialized
        else:
            return {"success": False, "message": "drone not initialized"}
        

    def process_detection(self, data):
        drone_info = data["droneInformation"]
        identification = drone_info["identification"]
        detection = data["detectedPositions"]
        #detection is like {
        # "red" : {
        # "x" : 0.5,
        # "y" : 0.4 
        # },
        # "blue" : {
        # "x" : 0.84,
        # "y" : 0.74
        # }
        # }

        #good to know : iterating through a python dict always give the same order of keys as long as the dict 
        # is not altered, which is why this works
        
        #FIRST : update drone coordinates according to color    
        colors = []
        for droneColor in detection : 
            colors.append(droneColor)
            #each "drone" is actually a color
            self.slave_drones[self.getDroneByColor(droneColor)].coordinates = {
                "x": detection[droneColor]["x"],
                "y": detection[droneColor]["y"]
            }

        #THEN : update target associated to drone
        #get (color, target) couple
        couples = self.best_pairing(detection, self.targets)
        print(couples)
        for couple in couples :
            droneName = self.getDroneByColor(colors[couple[0]])
            self.slave_drones[droneName].target = self.targets[couple[1]]
 
            
        #targets = detection["targets"]
        #couples = self.best_pairing(drone_detection, targets)
        return {"success": True, "message": "Anafi Detected"}
    

    def process_init(self, data):
        drone_info = data["droneInformation"]
        identification = drone_info["identification"]
        drone_type = drone_info["droneType"]
        position = drone_info["position"]

        if drone_type == "leader":
            if self.leader_drone is None:
                self.leader_drone = Drone(
                    identification["source"],
                    identification["team"],
                    drone_type,
                    position,
                )
                #self.target.append(data["target"])
                ##self.interface.insert_drone(self.leader_drone)
                self.position_queue.put(self.leader_drone)
                print("leader drone " + identification["source"] + " initialized")
                return {"success": True, "message": "leader drone initialized"}
            else : 
                print("leader drone already initialized : " + self.leader_drone.name)
                return {"success": False, "message": "leader drone already initialized"}
     

        if drone_type == "slave":
            if identification["source"] not in self.slave_drones:
                # add drone to drone's dictionnary
                new_drone = Drone(
                    identification["source"],
                    identification["team"],
                    drone_type,
                    position,
                    identification["color"].lower()
                )
                #self.interface.insert_drone(new_drone)
                self.slave_drones[identification["source"]] = new_drone
                print("slave drone " + identification["source"] + " initialized")
                return {"success": True, "message": "slave drone initialized"}
            else :
                print("slave drone with name " + identification["source"] + " already initialized")
                return {
                    "success": False,
                    "message": "slave drone with the same name already initialized",
                }
    

    def parse_data(self, data):
        if type(data) == str:
            return json.loads(data)
        else:
            return data
        

    def best_pairing(self, drone_detection, targets):
        distance_matrix = self.make_distance_matrix(drone_detection, targets)

        print("distances", distance_matrix)

        # get (drone, target) couples from hungarian algorithm (minimize sum of distances)
        couples = self.ha.hungarian_algorithm(distance_matrix)

        return couples
    

    def define_command(self, drone):
        #Not used at this point in time because GPS is not precise and reliable enough 

        # get relative position of target from drone, x (right) and y (down)
        target_relative_position = self.get_relative_position(drone)

        # with no change of referencial, longitude is x and latitude is y
        leader_drone_heading = self.position["heading"]

        latitude_command = target_relative_position["y"] * math.cos(
            -leader_drone_heading
        ) + target_relative_position["x"] * math.sin(-leader_drone_heading)
        longitude_command = target_relative_position["x"] * math.cos(
            -leader_drone_heading
        ) - target_relative_position["y"] * math.sin(-leader_drone_heading)


    def distance(self, drone_position, target):
        print(drone_position, target)
        return math.sqrt(
            (drone_position["x"] - target.x) ** 2
            + (drone_position["y"] - target.y) ** 2
        )   


    def make_distance_matrix(self, drone_detection, targets):
        distance_matrix = []    
        self.drone_order = []
        for droneColor in drone_detection:
            self.drone_order.append(droneColor)
            distance_matrix.append([])
            for target in targets:
                distance_matrix[-1].append(self.distance(self.slave_drones[self.getDroneByColor(droneColor)].coordinates, target))
        return distance_matrix
    

    def get_relative_position(self, drone):
        # CAREFUL : y axis is inverted to have the same referential as the drone, 
        # which means y>0 if the target is "above" the drone on the video
        return {"x": drone.target.x - drone.coordinates["x"], "y": -(drone.target.y - drone.coordinates["y"])}

    def get_heading_directive(self, drone):
        if self.leader_drone != None and type(self.slave_drones[drone].position["heading"]) == float :
            heading_difference = self.leader_drone.position["heading"] - self.slave_drones[drone].position["heading"]
            if heading_difference > 180 :
                return 180 - (self.leader_drone.position["heading"] - self.slave_drones[drone].position["heading"])
            elif heading_difference < -180 :
                return -180 - (self.leader_drone.position["heading"] - self.slave_drones[drone].position["heading"])
            
            return (self.leader_drone.position["heading"] - self.slave_drones[drone].position["heading"])
        else :
            print(0)
            return 0
    
    def get_move_directive(self, drone):
        x = self.slave_drones[drone].coordinates["x"]
        y = self.slave_drones[drone].coordinates["y"]
        right_directive = 0
        forward_directive = 0

        print("getting move directive for ", drone, "coordinates", x, y)
        #if no target is defined, do nothing
        if self.slave_drones[drone].target == None : 
            self.slave_drones[drone].coordinates["x"] = 0.5
            self.slave_drones[drone].coordinates["y"] = 0.5
            self.slave_drones[drone].directives["forwardDirective"] = forward_directive
            self.slave_drones[drone].directives["rightDirective"] = right_directive
            return str({
            "rightDirective" : 0,
            "forwardDirective" : 0
        })
        
        print("there is a target")
        #else, compute directive
        if x < max(0.01,self.slave_drones[drone].target.x - 0.1) :
            right_directive = 1/x
        elif x > min(1, self.slave_drones[drone].target.x + 0.1):
            right_directive = -1/(1-x)
        if y < max(0,self.slave_drones[drone].target.y - 0.1) :
            forward_directive = -1/y
        elif y > min(0.99, self.slave_drones[drone].target.y + 0.1) :
            forward_directive = 1/(1-y)
        print("directive after process : ", right_directive, forward_directive)

        # reset drone "percepted" position in case it is not detected anymore. If it is detected by the leader drone, should change right away.
        # This avoid the drone being stuck on a command if it is not detected anymore for some reason 
        self.slave_drones[drone].coordinates["x"] = self.slave_drones[drone].target.x
        self.slave_drones[drone].coordinates["y"] = self.slave_drones[drone].target.y
        self.slave_drones[drone].directives["forwardDirective"] = forward_directive
        self.slave_drones[drone].directives["rightDirective"] = right_directive

        return str({
            "rightDirective" : right_directive,
            "forwardDirective" : forward_directive
        })


    def heading_directive_json(self, drone_name):
        return str(self.slave_drones[drone_name].directives["headingDirective"])
    
    def getDroneByColor(self, color):
        for drone in self.slave_drones : 
            if self.slave_drones[drone].color == color:
                print("detected color", color, "as", drone)
                return drone
        print("no drone detected for", color)   
        return None


if __name__ == "__main__":
    dh = DataHandler()

    ##send leader init message
    message = """{
    "droneInformation": {
        "messageType": "init",
        "droneType": "leader",
        "identification": {
        "team": "test",
        "auth": "egtj-3jqa-z6fh-ete7-wrml",
        "source": "3_AIR_DRONE-PATROLLER_leader"
        },
        "position": {
        "latitude": 48.87912171673277,
        "longitude": 2.368739850635129,
        "altitude": 0.41066664457321167,
        "heading": 38.22674853914756
        }
    },
    "timestamp": 1688716411516,
    }"""

    dh.process_data(message)

    ##send slave init message
    message = """{
    "droneInformation": {
        "messageType": "init",
        "droneType": "slave",
        "identification": {
        "team": "test",
        "auth": "egtj-3jqa-z6fh-ete7-wrml",
        "source": "3_AIR_DRONE-PATROLLER_slave",
        "color": "red"
        },
        "position": {
        "latitude": 48.87912171673277,
        "longitude": 2.368739850635129,
        "altitude": 0.41066664457321167,
        "heading": 38.22674853914756
        }
    },
    "timestamp": 1688716411516
    }"""

    dh.process_data(message)

    
