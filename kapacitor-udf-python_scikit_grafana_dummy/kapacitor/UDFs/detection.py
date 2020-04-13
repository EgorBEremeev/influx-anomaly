from kapacitor.udf.agent import Agent, Handler
from scipy import stats
import math
from kapacitor.udf import udf_pb2
import sys

#Imports for the ADS model
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger()

class ADSHandler(Handler):
    """
    Keep a rolling window of historically normal data
    When a new window arrives use a IsolationForest Model to determine
    anomaly score for every window point.
    """

    #Empty var for the ADS-Model
    model = None

    class state(object):
        def __init__(self):
            self._batch = []

        def reset(self):
            self._batch = []

        def update(self, value, point):
            self._batch.append((value, point))

        def get_point_values(self):
            values = list(map(lambda x: x[0], self._batch))
            return values

        def get_points(self):
            points = list(map(lambda x: x[1], self._batch))
            return points


    def __init__(self, agent):
        self._agent = agent
        self._field = ''

        # This loads the pretrained model.
        # Loading the model at the __init__ saves a lot of work
        self.model = joblib.load('/var/lib/kapacitor/model/adsmodel.pkl')
        self._state = ADSHandler.state()

        #self._points = []

    def info(self):
        """
        Respond with which type of edges we want/provide and any options we have.
        """
        response = udf_pb2.Response()
        # We will consume batch edges aka windows of data.
        response.info.wants = udf_pb2.BATCH
        # We will produce single points of data aka stream.
        response.info.provides = udf_pb2.STREAM

        # Here we can define options for the UDF.
        # Define which field we should process
        response.info.options['field'].valueTypes.append(udf_pb2.STRING)

        # Since we will be computing a moving average let's make the size configurable.
        # Define an option 'size' that takes one integer argument.
        # response.info.options['size'].valueTypes.append(udf_pb2.INT)

        return response

    def init(self, init_req):
        """
        Given a list of options initialize this instance of the handler
        """
        success = True
        msg = ''
        #size = 0
        for opt in init_req.options:
            if opt.name == 'field':
                self._field = opt.values[0].stringValue
            # elif opt.name == 'size':
            #     size = opt.values[0].intValue


        # if size <= 1:
        #     success = False
        #     msg += ' must supply window size > 1'
        if self._field == '':
            success = False
            msg += ' must supply a field name'

        response = udf_pb2.Response()
        response.init.success = success
        response.init.error = msg[1:]

        return response

    def snapshot(self):
        response = udf_pb2.Response()
        response.snapshot.snapshot = ''.encode()
        return response

    def restore(self, restore_req):
        response = udf_pb2.Response()
        response.restore.success = True
#        response.restore.error = 'not implemented'
        return response

    def begin_batch(self, begin_req):
        # logger.debug(f'Batch with following meta is begins: name={begin_req.name}, group={begin_req.group}, size={begin_req.size}' )
        # create new window for batch
        self._state.reset()

    def point(self, point):
        # Handling of the data when each point arrives at the script
        # Alternatively we can also run the ADS here but running it at end_batch is more efficient
        value = point.fieldsDouble[self._field]
        self._state.update(value, point)

    def end_batch(self, batch_meta):

        # Converting the internal lists of data points and it's values into numpy array

        values = self._state.get_point_values()
        points = self._state.get_points()

        x_data = np.array(values)

        # Check if the array contains NAN and replace them with 0 (or any other value)
        # If we remove the NAN the predictions array would have another shape than the input array from kapacitor
        if np.isnan(x_data).any() == True:
            x_data = np.nan_to_num(x_data, nan=0.0)

        # Reshape the data so the array is correct for the ADS-Model
        # Reshape since we only have one feature
        x_data = x_data.reshape(-1,1)

        # Returns -1 for outliers and 1 for inliers.
        predictions = self.model.predict(x_data)
        probas = self.model.decision_function(x_data)

        #logger.debug(f'Processed Batch contatins {len(points)} points, {len(predictions)} predictions, {len(probas)} probas' )

        prev_point_time = 0
        for label, score, point in zip(predictions, probas, points):
            response = udf_pb2.Response()
            # response.point.time = batch_meta.tmax
            # response.point.name = batch_meta.name
            # response.point.group = batch_meta.group
            # response.point.tags.update(batch_meta.tags)
            point_to_send = udf_pb2.Point()
            point_to_send.CopyFrom(point)
            point_to_send.ClearField('fieldsDouble')
            point_to_send.ClearField('fieldsInt')
            point_to_send.ClearField('fieldsString')
            point_to_send.ClearField('fieldsBool')
            point_to_send.fieldsDouble["point_label"] = label
            point_to_send.fieldsDouble["period_label"] = label
            point_to_send.fieldsDouble["score"] = score

            response.point.CopyFrom(point_to_send)

            self._agent.write_response(response)

            # Field "period_label" indicates the time frame to highlight on a graph as anomaly
			# The idea is that anomaly period starts at the last normal point.
			# So, getting anomaly point we rewrite "period_label" of the previous point. 
			# As Influx use point.time as a key field we send new "period_label" with time from the previous point.
			if label == -1:
                response = udf_pb2.Response()

                point_to_send = udf_pb2.Point()
                point_to_send.CopyFrom(point)
                point_to_send.ClearField('fieldsDouble')
                point_to_send.ClearField('fieldsInt')
                point_to_send.ClearField('fieldsString')
                point_to_send.ClearField('fieldsBool')
                point_to_send.time = prev_point_time
                point_to_send.fieldsDouble["period_label"] = label

                response.point.CopyFrom(point_to_send)

                self._agent.write_response(response)

            prev_point_time = point.time

if __name__ == '__main__':
    # Create an agent
    agent = Agent()

    # Create a handler and pass it an agent so it can write points
    h = ADSHandler(agent)

    # Set the handler on the agent
    agent.handler = h

    logger.info("Starting Agent with ADSHandler")
    agent.start()
    agent.wait()
    logger.info("Agent finished with ADSHandler")
