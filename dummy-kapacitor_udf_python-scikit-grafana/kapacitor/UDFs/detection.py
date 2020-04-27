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
    When a new window arrives use a two-sided t-test to determine
    if the new window is statistically significantly different.
    """

    #Empty var for the ADS-Model
    model = None

    class state(object):
        def __init__(self):
            self._batch = []
            self._last_anomaly_starts = None
            self._last_anomaly_ends = None

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

        def reset_anomaly_period(self):
            self._last_anomaly_starts = None
            self._last_anomaly_ends = None


    def __init__(self, agent):
        self._agent = agent
        self._field = ''

        # This loads the pretrained model.
        # Loading the model at the __init__ saves a lot of work
        self.model = joblib.load('/var/lib/kapacitor/UDFs/adsmodel.pkl')
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

        for opt in init_req.options:
            if opt.name == 'field':
                self._field = opt.values[0].stringValue

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
#        logger.debug(f'Batch with following meta is begins: name={begin_req.name}, group={begin_req.group}, size={begin_req.size}' )
        # create new window for batch
        self._state.reset()

    def point(self, point):
        # Handling of the data when each point arrives at the script
        # Alternatively we can also run the ADS here but running it at end_batch is more efficient
#        logger.debug(f'Point message fields: {point.name}, {point.group}, {point.database}, {point.dimensions}' )
        value = point.fieldsDouble[self._field]
        self._state.update(value, point)

    def end_batch(self, batch_meta):

        # Converting the internal list of data points into numpy array
        #values = list(map(lambda x: x[0], self._batch))
        #points = list(map(lambda x: x[1], self._batch))
        values = self._state.get_point_values()
        points = self._state.get_points()

        x_data = np.array(values)

        # Check if the array contains NAN and replace them with 0 (or any other value)
        # If we remove the NAN the predictions array would have another shape than the input array from kapacitor
        if np.isnan(x_data).any() == True:
            x_data = np.nan_to_num(x_data, nan=0.0)

        # Reshape the data so the array is correct for the ADS-Model
        # Reshape since we only have on feature
        x_data = x_data.reshape(-1,1)

        # Returns -1 for outliers and 1 for inliers.
        predictions = self.model.predict(x_data)
        probas = self.model.decision_function(x_data)

#        logger.debug(f'Processed Batch contatins {len(points)} points, {len(predictions)} predictions, {len(probas)} probas' )

        prev_point_time = 0
        for label, score, point in zip(predictions, probas, points):
            # Check the criteria the anomaly period has began and ended
            # If anomaly perion has not detected yet
            if self._state._last_anomaly_starts is None:
                # And if the first anomaly point has come
                if label == -1:
                    # Then it is a criteria for anomaly period has began
                    logger.debug(f'Anomaly period has began at: {self._state._last_anomaly_starts}')
                    self._state._last_anomaly_starts = prev_point_time
            # If anomaly period is already detected
            else:
                # And if next incoming point is detected as normal = as non-anomaly that it is criteria for anomaly period is over
                if label == 1:
                    logger.debug(f'Anomaly period that has began at: {self._state._last_anomaly_starts} has ended at: {point.time}. The point.time is: {point.time}. The label is: {label}')
                    self._state._last_anomaly_ends = prev_point_time

            # We send anomaly period metadata point when the period has ended
            if self._state._last_anomaly_ends is not None:
                # Then we send point with metadata about the anomaly period on the whole to be stored in the separate measurement.
                # The measurement this point to be saved defined in the scope of Kapacitor Task!
                # There point from the this UDF_Node filtered by the presence of "anomaly_ends" field:
                # where(lambda: isPresent("anomaly_ends"))
                response = udf_pb2.Response()
                # timestamp to be used in measurement with anomaly perion metadata we set to the timestamp of the last anomaly point
                response.point.time = self._state._last_anomaly_ends
                response.point.fieldsInt["anomaly_begins"] = self._state._last_anomaly_starts
                # using prev_point_time below affects visualization - visually the end of period is shown covering entire anomaly period, but not going out a one time step ahead
                response.point.fieldsInt["anomaly_ends"] = self._state._last_anomaly_ends
                self._agent.write_response(response)

                # Update state that the last anomaly period has ended
                self._state.reset_anomaly_period()

            # We send additional anomaly attributes as new fields and tags to every point in the main value measurement
            response = udf_pb2.Response()
            response.point.time = point.time
            response.point.fieldsDouble["point_label"] = label
            response.point.fieldsDouble["score"] = score
            self._agent.write_response(response)

            # timestamp to be used for "period_label" points is set to the one time step back
            # the begin of anamaly period is shown as last normal point
            # the end of anomaly perion is shown as last anomaly point
            # with this visually we see the period non-shifted relativly to the values graph

            response = udf_pb2.Response()
            response.point.time = prev_point_time
            response.point.fieldsDouble["period_label"] = label
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
