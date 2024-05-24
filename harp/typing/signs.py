class Sign(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


NotSet = Sign("NotSet")
Maybe = Sign("Maybe")
Default = Sign("Default")
