# from os import listdir, path
# from json import dump as dump_json, load as load_json

from .finder import HiveFinder


class ProjectManager:

    config_file_name = "hive_project.json"

    def __init__(self, project_path=None):
        self.project_name = project_path

        if project_path is None:
            self.hive_finder = HiveFinder()

        else:
            self.hive_finder = HiveFinder(project_path)
