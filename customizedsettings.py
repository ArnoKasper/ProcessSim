class CustomizedSettings(object):
    def __init__(self, simulation):
        self.sim = simulation

    def pool_seq_rule(self, order):
        """
        Define customized version of pool priority. No dynamic updating
            - if return is None, the default is used as specified in the control panel
        :param order: order object
        :return: sequence priority
        """
        return None

    def queue_priority(self, order):
        """
        Define customized version of queue priority. No dynamic updating
            - if return is None, the default is used as specified in the control panel
        :param order: order object
        :return: queue priority
        """
        return None

    def dispatching_mode(self, queue_list):
        """
        Define customized version of queue priority. Dynamic updating
            - if return is None, the default is used as specified in the control panel
        :param queue_list: list with all orders in the queue
        :return: updated queue_list
        """
        return None

    def due_date(self, order):
        """
        Define customized version of due date modeling
            - if return is None, the default is used as specified in the control panel
        :param order: order object
        :return:
        """
        return None