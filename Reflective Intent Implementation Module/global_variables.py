import time


def singleton(cls):
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class GlobalVariables(object):
    """
    This class holds global variables that can be accessed and modified throughout the application.
    It is used to maintain state across different parts of the code.
    """
    
    def __init__(self):
        self.attachments_for_verifier = []
        self.scenario = ""
        self.platform = ""
        self.diagram_type = ""
        self.model = ""
        self.run_number = 1 #to be modified on demand
        self.iteration = 1 #agent's internal logic 0 do not midify manualy
        self.start_time = 0
        self.end_time = 0
        self.implementation_thread_id = None
        self.verifier_thread_id  = None
        
    
    def set_attachments_for_verifier(self, attachments):
        self.attachments_for_verifier = attachments
    
    def get_attachments_for_verifier(self):
        return self.attachments_for_verifier
    
    def add_attachment_for_verifier(self, attachment):
        self.attachments_for_verifier.append(attachment)
    
    def clear_attachments_for_verifier(self):
        self.attachments_for_verifier.clear()
    
    def set_scenario(self, scenario_name):
        self.scenario = scenario_name
        
    def get_scenario(self):
        return self.scenario
    
    def set_platform(self, platform_name):
        self.platform = platform_name
        
    def get_platform(self):
        return self.platform
    
    def set_diagram_type(self, diagram_type):
        self.diagram_type = diagram_type
        
    def get_diagram_type(self):
        return self.diagram_type
    
    def set_model(self, model_name):
        self.model = model_name
        
    def get_model(self):
        return self.model
    
    def set_run_number(self, run_number):
        self.run_number = run_number
        
    def get_run_number(self):
        return self.run_number
    
    def set_iteration(self, iteration):
        self.iteration = iteration
        
    def get_iteration(self):
        return self.iteration
    
    def increment_iteration(self):
        self.iteration += 1
        
    def start_timer(self):
        self.start_time = time.time()
    
    def end_timer(self):
        self.end_time = time.time()
    
    def get_elapsed_time(self):
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time
    
    def set_implementation_thread_id(self, thread_id):
        self.implementation_thread_id = thread_id
    def get_implementation_thread_id(self):
        return self.implementation_thread_id
    def set_verifier_thread_id(self, thread_id):
        self.verifier_thread_id = thread_id
    def get_verifier_thread_id(self):
        return self.verifier_thread_id
    
    def current_run_dir_path(self):
        return f"Implementation_results/{self.model}/{self.platform}/{self.diagram_type}/(Run{self.run_number})/{self.scenario}"
    
        
    