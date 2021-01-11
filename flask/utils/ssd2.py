"""ssd2.py
"""

import re
import ctypes

import numpy as np
import tensorflow as tf
from PIL import Image

class TfSSD2(object):
    """TfSSD class encapsulates things needed to run TensorFlow SSD."""

    def __init__(self, model, input_shape):
        self.model = model
        self.input_shape = input_shape

        # load detection graph
        self.ssd_graph = tf.Graph()
        with self.ssd_graph.as_default():
            graph_def = tf.GraphDef()
            with tf.gfile.GFile('ssd/%s.pb' % model, 'rb') as fid:
                serialized_graph = fid.read()
                graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(graph_def, name='')

        # create the session for inferencing
        #self.sess = tf.Session(graph=self.ssd_graph)
        # define input/output tensors
        #self.det_boxes = self.ssd_graph.get_tensor_by_name('detection_boxes:0')
        #self.det_scores = self.ssd_graph.get_tensor_by_name('detection_scores:0')
        #self.det_classes = self.ssd_graph.get_tensor_by_name('detection_classes:0')


    #def __del__(self):
        #self.sess.close()

    @staticmethod
    def load_image_into_numpy_array(image):
        (im_width, im_height) = image.size
        return np.array(image.getdata()).reshape(
                (im_height, im_width, 3)).astype(np.uint8)

    def detect(self, image, conf_th=0.2):
        # the array based representation of the image will be used later in order to prepare the
        # result image with boxes and labels on it.
        image = image.resize( (300,300) )
        image = TfSSD2.load_image_into_numpy_array(image)
        # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
        image_np_expanded = np.expand_dims(image, axis=0)

        with self.ssd_graph.as_default():
            with tf.Session() as sess:
                # Get handles to input and output tensors
                #ops = tf.get_default_graph().get_operations()
                ops = self.ssd_graph.get_operations()
                all_tensor_names = {
                    output.name for op in ops for output in op.outputs}
                tensor_dict = {}
                for key in [
                    'num_detections', 'detection_boxes', 'detection_scores',
                    'detection_classes', 'detection_masks'
                ]:
                    tensor_name = key + ':0'
                    if tensor_name in all_tensor_names:
                        tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
                            tensor_name)
                if 'detection_masks' in tensor_dict:
                    # The following processing is only for single image
                    detection_boxes = tf.squeeze(
                        tensor_dict['detection_boxes'], [0])
                    detection_masks = tf.squeeze(
                        tensor_dict['detection_masks'], [0])
                    # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
                    real_num_detection = tf.cast(
                        tensor_dict['num_detections'][0], tf.int32)
                    detection_boxes = tf.slice(detection_boxes, [0, 0], [
                                               real_num_detection, -1])
                    detection_masks = tf.slice(detection_masks, [0, 0, 0], [
                                               real_num_detection, -1, -1])
                    detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
                        detection_masks, detection_boxes, image.shape[0], image.shape[1])
                    detection_masks_reframed = tf.cast(
                        tf.greater(detection_masks_reframed, 0.5), tf.uint8)
                    # Follow the convention by adding back the batch dimension
                    tensor_dict['detection_masks'] = tf.expand_dims(
                        detection_masks_reframed, 0)
                image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

                # Run inference
                output_dict = sess.run(tensor_dict,
                                       feed_dict={image_tensor: np.expand_dims(image, 0)})

                # all outputs are float32 numpy arrays, so convert types as appropriate
                output_dict['num_detections'] = int(
                    output_dict['num_detections'][0])
                output_dict['detection_classes'] = output_dict[
                    'detection_classes'][0].astype(np.uint8)
                output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
                output_dict['detection_scores'] = output_dict['detection_scores'][0]
                if 'detection_masks' in output_dict:
                    output_dict['detection_masks'] = output_dict['detection_masks'][0]
        return output_dict

