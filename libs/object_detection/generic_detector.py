import cv2 as cv
import numpy as np
import os

class GenericDetector:

    def __init__(
        self,
        conf_thresh=0.5,
        nms_thresh=0.4,
        inp_width=416,
        inp_height=416,
        model_config='nn_data/yolov3.cfg',
        model_weights='nn_data/yolov3.weights',
        classes_file='nn_data/coco.names'):

        dir_path = os.path.dirname(os.path.realpath(__file__))

        self.conf_thresh = conf_thresh
        self.nms_thresh = nms_thresh
        self.inp_width = inp_width
        self.inp_height = inp_height
        
        with open(dir_path + '/' + classes_file, 'rt') as f:
            self.classes = f.read().rstrip('\n').split('\n')

        self.net = None

        self._initialize_model(
            dir_path + '/' + model_config,
            dir_path + '/' + model_weights)

    """
    Public Functions
    """
    
    def get_bounding_boxes(self, media_file):
        cap = cv.VideoCapture(media_file)

        frame_boxes = []

        while cv.waitKey(1) < 0:
            has_frame, frame = cap.read()
        
            if not has_frame:
                cap.release()
                break 

            frame_boxes.append(self.process_frame(frame))

        return frame_boxes

    # processes a cv frame
    def process_frame(self, frame, out_file=None):
        # Create a 4D blob from a frame.
        blob = cv.dnn.blobFromImage(
            frame,
            1/255, 
            (self.inp_width, self.inp_height),
            [0,0,0],
            1,
            crop=False)

        # Sets the input to the network
        self.net.setInput(blob)

        # Runs the forward pass to get output of the output layers
        outs = self.net.forward(self._get_outputs_names(self.net))

        # Remove the bounding boxes with low confidence
        boxes = self._post_process(frame, outs)

        # get inference time for DEBUG
        t, _ = self.net.getPerfProfile()
        label = '%.2f ms' % (t * 1000.0 / cv.getTickFrequency())

        cv.putText(frame, label, (50,50), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2, cv.LINE_AA)

        if out_file is not None:
            cv.imwrite(out_file, frame.astype(np.uint8))

        return boxes

    """
    Helper Functions
    """
    
    def _initialize_model(self, model_config, model_weights):
        self.net = cv.dnn.readNetFromDarknet(model_config, model_weights)
        self.net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv.dnn.DNN_TARGET_CPU)

    # Get the names of the output layers
    def _get_outputs_names(self, net):
        # Get the names of all the layers in the network
        layersNames = net.getLayerNames()
        # Get the names of the output layers, i.e. the layers with unconnected outputs
        return [layersNames[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    # Remove the bounding boxes with low confidence using non-maxima suppression
    def _post_process(self, frame, outs):
        frameHeight = frame.shape[0]
        frameWidth = frame.shape[1]

        # Scan through all the bounding boxes output from the network and keep only the
        # ones with high confidence scores. Assign the box's class label as the class with the highest score.
        classIds = []
        confidences = []
        boxes = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                classId = np.argmax(scores)
                confidence = scores[classId]
                if confidence > self.conf_thresh:
                    center_x = int(detection[0] * frameWidth)
                    center_y = int(detection[1] * frameHeight)
                    width = int(detection[2] * frameWidth)
                    height = int(detection[3] * frameHeight)
                    left = int(center_x - width / 2)
                    top = int(center_y - height / 2)
                    classIds.append(classId)
                    confidences.append(float(confidence))
                    boxes.append([int(left), int(top), int(width), int(height)])

        # Perform non maximum suppression to eliminate redundant overlapping boxes with
        # lower confidences.
        indices = cv.dnn.NMSBoxes(boxes, confidences, self.conf_thresh, self.nms_thresh)
   
        final_boxes = []

        for i in indices:
            i = i[0]
            box = boxes[i]

            if self.classes:
                assert(classIds[i] < len(self.classes))

            final_boxes.append(
                [
                    int(classIds[i]), 
                    self.classes[classIds[i]],
                    float(confidences[i]),
                    box
                ]
            )

            # drawing on image
            left = box[0]
            top = box[1]
            width = box[2]
            height = box[3]
            self._draw_pred(frame, classIds[i], confidences[i], left, top, left + width, top + height)
        return final_boxes

    # Draw the predicted bounding box, can be used to view bounding boxes
    def _draw_pred(self, frame, classId, conf, left, top, right, bottom):
        # Draw a bounding box.
        cv.rectangle(frame, (left, top), (right, bottom), (255, 178, 50), 3)
        
        label = '%.2f' % conf
            
        # Get the label for the class name and its confidence
        if self.classes:
            assert(classId < len(self.classes))
            label = '%s:%s' % (self.classes[classId], label)

        #Display the label at the top of the bounding box
        labelSize, baseLine = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        top = max(top, labelSize[1])
        cv.rectangle(frame,
            (left, top - round(1.5*labelSize[1])),
            (left + round(1.5*labelSize[0]),
            top + baseLine), (255, 255, 255), cv.FILLED)
        cv.putText(frame, label, (left, top), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0,0,0), 1)
