class CustomizedSettings(object):
    def __init__(self, simulation):
        self.sim = simulation

    def pool_seq_rule(self, order):
        """
        Define customized version of pool priority. No dynamic updating
        :param order: order object
        :return: sequence priority
        """
        return

    def queue_priority(self, order):
        """
        Define customized version of queue priority. No dynamic updating
        :param order: order object
        :return: queue priority
        """
        return

    def dispatching_mode(self, queue_list):
        """
        Define customized version of queue priority. Dynamic updating
        :param queue_list: list with all orders in the queue
        :return: updated queue_list
        """
        return