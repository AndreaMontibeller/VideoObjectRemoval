# Test image detection implementation
import cv2
from time import time, sleep
from glob import glob
import numpy as np
import ObjectDetection.imutils as imu
from ObjectDetection.detect import DetectSingle, TrackSequence, GroupSequence
from ObjectDetection.inpaintRemote import InpaintRemote
from threading import Thread

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return

test_imutils = False
test_single = False
test_dilateErode = False
test_sequence = False
test_grouping = False 
test_bbmasks =  False
test_maskFill = False 
test_maskoutput = False 
test_remoteInpaint = True 

if test_imutils:
    bbtest = [0.111, 0.123, 0.211, 0.312]
    bbc = imu.bboxCenter(bbtest)
    print(bbc)

if test_single:
    detect = DetectSingle(selectObjectNames=['person','car'])
    imgfile = "../data/input.jpg"
    detect.predict(imgfile)
    imout = detect.annotate()

    cv2.imshow('results',imout)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    imout = detect.visualize_all(scale=1.2)
    cv2.imshow('results',imout)
    cv2.waitKey(0)
    cv2.destroyAllWindows(); 

if test_dilateErode:
    detect = DetectSingle(selectObjectNames=['person','car'])
    imgfile = "../data/input.jpg"
    detect.predict(imgfile)
    masks = detect.masks
    mask = imu.combineMasks(masks)

    orig = "original"
    modf = "DilationErosion"
    cv2.namedWindow(orig)
    cv2.namedWindow(modf)
    
    # single dilation operation
    modmask = imu.dilateErodeMask(mask)  
    cv2.imshow(orig,imu.maskToImg(mask))
    cv2.imshow(modf,imu.maskToImg(modmask))
    cv2.waitKey(0)

    modmask = imu.dilateErodeMask(mask,actionList=['dilate','erode','dilate'])  
    cv2.imshow(orig,imu.maskToImg(mask))
    cv2.imshow(modf,imu.maskToImg(modmask))
    cv2.waitKey(0)

    cv2.destroyAllWindows()


if test_sequence:
    fnames = sorted(glob("../data/Colomar/frames/*.png"))[200:400]
    trackseq = TrackSequence(selectObjectNames=['person','car'])
    trackseq.predict_sequence(filelist=fnames)
    res = trackseq.get_sequenceResults()

if test_grouping:
    fnames = sorted(glob("../data/Colomar/frames/*.png"))[200:400]
    groupseq = GroupSequence(selectObjectNames=['person','car'])
    groupseq.load_images(filelist=fnames)
    groupseq.groupObjBBMaskSequence(useBBmasks=test_bbmasks)
    res = groupseq.get_groupedResults(getSpecificObjNames='person')

if test_grouping and test_maskFill:
    groupseq.filter_ObjBBMaskSeq(allowObjNameInstances={'person':[2]},minCount=70)
    #groupseq.fill_ObjBBMaskSequence(specificObjectNameInstances={'person':[0,1,2]})
    groupseq.fill_ObjBBMaskSequence()

if test_grouping and test_maskoutput:
    groupseq.combine_MaskSequence()
    groupseq.dilateErode_MaskSequence(kernelShape='elipse',maskHalfWidth=10)
    groupseq.write_ImageMaskSequence(cleanDirectory=True,
        writeImagesToDirectory="../data/Colomar/fourInpaint/frames",
        writeMasksToDirectory="../data/Colomar/fourInpaint/masks")
    groupseq.create_animationObject(MPEGfile="../data/Colomar/result.mp4")

if test_remoteInpaint:
    rinpaint = InpaintRemote() 
    rinpaint.connectInpaint()

    frameDirPath="/home/appuser/data/Colomar/threeInpaint/frames"
    maskDirPath="/home/appuser/data/Colomar/threeInpaint/masks"

    trd1 = ThreadWithReturnValue(target=rinpaint.runInpaint,
                                 kwargs={'frameDirPath':frameDirPath,'maskDirPath':maskDirPath})
    trd1.start() 

    print("working:",end='',flush=True)
    while trd1.is_alive():
        print('.',end='',flush=True)
        sleep(1)

    print("\nfinished")
    rinpaint.disconnectInpaint()

    stdin,stdout,stderr = trd1.join()
    ok = False
    for l in stdout:
        if "Propagation has been finished" in l: 
            ok = True
        print(l.strip())

print("done")
