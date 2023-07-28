class Drone:
    def __init__(self, name, team, type, position, color=None):
        self.name = name
        self.team = team
        self.type = type
        # position is a dictionnary with keys "latitude", "longitude", "altitude" and "heading"
        self.position = position
        # coordinates is a dictionnary with keys "x" and "y" in camera referential
        self.coordinates = {"x": 0.5, "y": 0.5}
        self.color = color
        self.target = None
        self.headingDirective = 0
    

