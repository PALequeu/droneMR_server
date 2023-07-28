import json
from hungarian_algorithm import HungarianAlgorithm
import math
from drone import Drone
from target import Target


class DataHandler:
    def __init__(self):
        self.ha = HungarianAlgorithm()
        self.number_of_slaves = 0
        self.leader_drone = None
        self.slave_drones = {}
        self.target = Target(1,0,0)
        

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

            for drone in self.slave_drones :
                self.slave_drones[drone].headingDirective = self.get_heading_directive(drone)
    
            return {"success": True, "message": "drone position updated"}

        # else check if drone is slave drone
        
        elif identification["source"] in self.slave_drones:
            # update drone's position
            self.slave_drones[identification["source"]].position = position
            print(identification["source"] + " position update") 
            return {"success": True, "message": "drone position updated"}

        # else drone is not initialized
        else:
            return {"success": False, "message": "drone not initialized"}
        

    def process_detection(self, data):
        drone_info = data["droneInformation"]
        identification = drone_info["identification"]
        detection = data["detectedPositions"]

        for position in detection :
            print(detection[position])
            for drone in self.slave_drones :
                self.slave_drones[drone].coordinates = {
                    "x": detection[position]["x"],
                    "y": detection[position]["y"]
                }

            
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
                    None, #TODO: color
                )
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

        # get (drone, target) couples from hungarian algorithm (minimize sum of distances)
        couples = self.ha.hungarian_algorithm(distance_matrix)

        return couples
    

    def define_command(self, drone, target):
        # get relative position of target from drone, x (right) and y (down)
        target_relative_position = self.get_relative_position(drone, target)

        # with no change of referencial, longitude is x and latitude is y
        leader_drone_heading = self.position["heading"]

        latitude_command = target_relative_position["y"] * math.cos(
            -leader_drone_heading
        ) + target_relative_position["x"] * math.sin(-leader_drone_heading)
        longitude_command = target_relative_position["x"] * math.cos(
            -leader_drone_heading
        ) - target_relative_position["y"] * math.sin(-leader_drone_heading)


    def distance(self, drone_position, target_position):
        return math.sqrt(
            (drone_position["x"] - target_position["x"]) ** 2
            + (drone_position["y"] - target_position["y"]) ** 2
        )


    def make_distance_matrix(self, drone_detection, targets):
        distance_matrix = []
        for drone in drone_detection:
            distance_matrix.append([])
            for target in targets:
                distance_matrix[-1].append(self.distance(drone, target))
        return distance_matrix

    def get_relative_position(self, drone, target):
        # CAREFUL : y axis is inverted tu have the same referential as the drone
        return {"x": target["x"] - drone["x"], "y": -(target["y"] - drone["y"])}

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
        if x < 0.4 :
            right_directive = 1/x
        elif x > 0.6 :
            right_directive = -1/(1-x)
        if y < 0.4 :
            forward_directive = -1/y
        elif y > 0.6 :
            forward_directive = 1/(1-y)
        return str({
            "rightDirective" : right_directive,
            "forwardDirective" : forward_directive
        })


    def heading_directive_json(self, drone_name):
        return str(self.slave_drones[drone_name].headingDirective)


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

    
