# Basic image utilities 

import os
from glob import glob
import subprocess as sp

# import some common libraries
import cv2
import numpy as np
from math import log10, ceil

fontconfig = {
    "fontFace"     : cv2.FONT_HERSHEY_SIMPLEX,
    "fontScale"    : 5, 
    "color"        : (0,0,255),
    "lineType"     : 3
}

# ---------------
# video editing tools

def get_fourcc_string(vfile):
    if not os.path.isdir(vfile):
        cap = cv2.VideoCapture(vfile)
        vcodec = cap.get(cv2.CAP_PROP_FOURCC)
        vcodecstr = "".join([chr((int(vcodec) >> 8 * i) & 0xFF) for i in range(4)])
        cap.release()
        return vcodecstr
    else:
        return None

def get_fps(vfile):
    if not os.path.isdir(vfile):
        cap = cv2.VideoCapture(vfile)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return fps
    else:
        return None


def get_nframes(vfile):
    if not os.path.isdir(vfile):
        cap = cv2.VideoCapture(vfile)
        n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
    else:
        images = glob(os.path.join(vfile, '*.jp*'))
        if not images:
            images = glob(os.path.join(vfile, '*.png')) 
        assert images, f"No image file (*.jpg or *.png) found in {vfile}"        
        n_frames = len(images)

    return n_frames 


def get_WidthHeight(vfile):
    if not os.path.isdir(vfile):
        cap = cv2.VideoCapture(vfile)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
    else:
        images = glob(os.path.join(vfile, '*.jp*'))
        if not images:
            images = glob(os.path.join(vfile, '*.png')) 
        assert images, f"No image file (*.jpg or *.png) found in {vfile}"        
        img = cv2.imread(images[0])
        height,width = img.shape[:2]

    return (width, height) 


def get_frame(vfile, n_frames, startframe=0, finishframe=None):
    if os.path.isdir(vfile):
        images = glob(os.path.join(vfile, '*.jp*'))
        if not images:
            images = glob(os.path.join(vfile, '*.png'))
        assert images, f"No image file (*.jpg or *.png) found in {vfile}"        

        assert len(images) == n_frames, \
            f"Mismatch in number of mask files versus number of frames\n" + \
            f"n_frames={n_frames}, n_masks={len(images)}"

        images = sorted(images,
                        key=lambda x: int(x.split('/')[-1].split('.')[0]))

        if finishframe is None:
            finishframe = n_frames        

        images = images[startframe:finishframe]

        for img in images:
            frame = cv2.imread(img)
            yield frame

    else:
        cap = cv2.VideoCapture(vfile)

        # start frame is indexed
        # stop frame is set by controlling loop (caller)
        if startframe != 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, startframe)
            i = startframe
        else: 
            i = 0
        
        while True:
            ret, frame = cap.read()
            
            if ret and i <= finishframe:
                yield frame
            else:
                cap.release()
                break 

            i +=1


# ------------
# Bounding box (bbox) and mask utilities
def bboxToList(bboxTensor):
    return  [float(x) for x in bboxTensor.to('cpu').tensor.numpy().ravel()]

def bboxCenter(bbox):
    """
        Returns (x_c,y_c) of center of bounding box list (x_0,y_0,x_1,y_1)
    """
    return [(bbox[0] + bbox[2])/2,(bbox[1] + bbox[3])/2]

def bboxIoU(boxA, boxB):
    """
        Returns Intersection-Over-Union value for bounding bounding boxA and boxB
        where boxA and boxB are formed by (x_0,y_0,x_1,y_1) lists 
    """
    # determine the (x, y)-coordinates of the intersection rectangle
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    
    # compute the area of intersection rectangle
    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    
    # compute the area of both the prediction and ground-truthrectangles
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
    
    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = interArea / float(boxAArea + boxBArea - interArea)
    
    # return the intersection over union value
    return iou

def bboxToMask(bbox,maskShape):
    """
        Creates a mask(np.bool) based on bbox area for equivalent mask shape
    """
    assert isinstance(bbox,list), "bbox must be list"
    assert isinstance(maskShape,(tuple, list)), "maskShape must be list or tuple"
    x0,y0,x1,y1 = [round(x) for x in bbox]

    bbmask = np.full(maskShape,fill_value=False, dtype=np.bool)
    bbmask[y0:y1,x0:x1] = True
    return bbmask


def combineMasks(maskList):
    """
        Combines the list of masks into a single mask
    """
    # single mask passed
    if not isinstance(maskList,list):
        return maskList   
    elif len(maskList) == 1:
        return maskList[0]     

    masks = [ m for m in maskList if len(m) ]
    maskcomb = masks.pop(0).copy() 
    for msk in masks:
        maskcomb = np.logical_or(maskcomb,msk)
    
    return maskcomb


def maskImage(im, mask, mask_color=(0,0,255), inplace=False):
    if inplace:
        outim = im
    else:
        outim = im.copy()

    if not isinstance(mask,list):
        for i in range(3):
            outim[:,:,i] = (mask > 0) * mask_color[i] + (mask == 0) * outim[:, :, i]

    return outim

def maskToImg(mask, toThreeChannel=False):
    """
        converts a mask(dtype=np.bool) to cv2 compatable image (dytpe=np.uint8)
        copies to a 3 channel array if requested
    """
    maskout = np.zeros_like(mask,dtype=np.uint8)
    if mask.dtype == np.bool:
        maskout = np.uint8(255*mask)
    else:
        maskout = np.uint8((mask > 0) * 255) 
    
    if toThreeChannel and len(maskout.shape) == 2:
        mmaskout = np.zeros([*maskout.shape,3],dtype=np.uint8)
        mmaskout[:,:,0] = maskout
        mmaskout[:,:,1] = maskout
        mmaskout[:,:,2] = maskout
        return mmaskout 
    else: 
        return maskout


def dilateErodeMask(mask, actionList=['dilate'], kernelShape='rect', maskHalfWidth=4):
    """
        Dilates or Erodes image mask ('mask') by 'kernelShape', based on mask width
        'maskWidth'= 2 * maskHalfWidth + 1
        'actionList' is a list of actions ('dilate' or 'erode') to perform on the mask
    """
    for act in actionList:
        assert act in ('dilate', 'erode'), "Invalid action specified in actionList"

    if kernelShape.lower().startswith('re'): 
        krnShape = cv2.MORPH_RECT       # rectangular mask
    elif kernelShape.lower().startswith('cr'): 
        krnShape = cv2.MORPH_CROSS      # cross shape
    elif kernelShape.lower().startswith('el'):
        krnShape = cv2.MORPH_ELLIPSE    # elliptical shape (or circlular)
    else:
        raise Exception(f"Unknown kernel mask shape specified: {kernelShape}")

    assert maskHalfWidth > 0, "Error: maskHalfWidth must be > 0" 

    maskWasDtype = mask.dtype
    maskWidth = 2 * maskHalfWidth + 1
    krnElement = cv2.getStructuringElement(krnShape, 
                                           (maskWidth,maskWidth),  
                                           (maskHalfWidth, maskHalfWidth))

    maskout = np.uint8(mask.copy())
    for act in actionList:
        if act == 'dilate': 
            maskout = cv2.dilate(maskout,krnElement)
        elif act == 'erode': 
            maskout = cv2.erode(maskout,krnElement)
        else:
            pass  # hmm, shouldn't get here

    maskout.dtype = maskWasDtype
    return maskout


def videofileToFramesDirectory(videofile,dirPath,padlength=5,imgtype='png',cleanDirectory=True):
    """
        writes a video file (.mp4, .avi, or .mov) to frames directory
        Here, it is understood that images are an np.array, dtype='uint8' 
        of shape (w,h,3)
    """
    assert imgtype in ('png', 'jpg'), f"Invalid image type '{imgtype}' given"

    if not os.path.isdir(dirPath):
        path = '/' if dirPath.startswith("/") else ''
        for d in dirPath.split('/'):
            if not d: continue
            path += d + '/'
            if not os.path.isdir(path):
                os.mkdir(path)
    elif cleanDirectory:
        for f in glob(os.path.join(dirPath,"*." + imgtype)):
            os.remove(f) # danger Will Robinson

    cap = cv2.VideoCapture(videofile)
    n = 0
    while True:
        ret,frame = cap.read()

        if not ret:
            cap.release()
            break
        fname = str(n).rjust(padlength,'0') + '.' + imgtype
        cv2.imwrite(os.path.join(dirPath,fname),frame)

        n += 1

    return n


def writeImagesToDirectory(imageList,dirPath,minPadLength=None,imgtype='png',cleanDirectory=False):
    """
        writes flat list of image arrays to directory
        Here, it is understood that images are an np.array, dtype='uint8' 
        of shape (w,h,3)
    """
    assert imgtype in ('png', 'jpg'), f"Invalid image type '{imgtype}' given"

    if not os.path.isdir(dirPath):
        path = '/' if dirPath.startswith("/") else ''
        for d in dirPath.split('/'):
            if not d: continue
            path += d + '/'
            if not os.path.isdir(path):
                os.mkdir(path)
    elif cleanDirectory:
        for f in glob(os.path.join(dirPath,"*." + imgtype)):
            os.remove(f) # danger Will Robinson

    n_frames = len(imageList)
    padlength = ceil(log10(n_frames)) if minPadLength is None else minPadLength    
    for i,img in enumerate(imageList):
        fname = str(i).rjust(padlength,'0') + '.' + imgtype
        fname = os.path.join(dirPath,fname)
        cv2.imwrite(fname,img)
    
    return n_frames


def writeMasksToDirectory(maskList,dirPath,minPadLength=None,imgtype='png',cleanDirectory=False):
    """
        writes flat list of mask arrays to directory
        Here, it is understood that mask is an np.array,dtype='bool'
        of shape (w,h), will be output to (w,h,3) for compatibility
    """
    assert imgtype in ('png', 'jpg'), f"Invalid image type '{imgtype}' given"

    if not os.path.isdir(dirPath):
        path = '/' if dirPath.startswith("/") else ''
        for d in dirPath.split('/'):
            if not d: continue
            path += d + '/'
            if not os.path.isdir(path):
                os.mkdir(path)
    elif cleanDirectory:
        for f in glob(os.path.join(dirPath,"*." + imgtype)):
            os.remove(f) # danger Will Robinson

    n_frames = len(maskList)
    padlength = ceil(log10(n_frames)) if minPadLength is None else minPadLength    
    for i,msk in enumerate(maskList):
        fname = str(i).rjust(padlength,'0') + '.' + imgtype
        fname = os.path.join(dirPath,fname)
        cv2.imwrite(fname,msk * 255)
    
    return n_frames


def writeFramesToVideo(imageList,filePath,fps=30,
                       fourccstr=None, useFFMPEGdirect=False):
    """
        Writes given set of frames to video file (platform specific coding)
        format is 'mp4' or 'avi'
    """
    assert len(imageList) > 1, "Cannot make video with single frame"
    height,width =imageList[0].shape[:2]

    dirPath = os.path.dirname(filePath)
    if not os.path.isdir(dirPath):
        path = ''
        for d in dirPath.split('/'):
            if not d: continue
            path += d + '/'
            if not os.path.isdir(path):
                os.mkdir(path)

    if useFFMPEGdirect: 
        # use ffmpeg installed in container (assuming were in container)
        # the ffmpeg, as compiled for Linux, contains the H264 codec 
        # as available in the libx264 library
        assert filePath.endswith(".mp4"), "Cannot use non-mp4 formats with ffmpeg"

        # assume image list is from OpenCV read.  Thus reverse the channels for the correct colors
        clip = [ im[:, :, ::-1] for im in imageList]
        h,w = clip[0].shape[:2] 

        clippack = np.stack(clip)
        out,err = __ffmpegDirect(clippack,outputfile=filePath,fps=fps, size=[h,w])
        assert os.path.exists(filePath), print(err) 

    else:
        # use openCV method
        # this works, but native 'mp4v' codec is not compatible
        # with html.Video().  H264 codec is not availabe with OpenCV 
        # unless you compile it from source (GPL issues)
        if filePath.endswith(".mp4"):
            if fourccstr is None:
                fourccstr = 'mp4v' 
            fourcc = cv2.VideoWriter_fourcc(*fourccstr)
        elif filePath.endswith(".avi"):
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
        else:
            assert False, f"Could not determine the video output type from {filePath}"
        
        outvid = cv2.VideoWriter(filePath, fourcc, fps, (width,height) )

        # write out frames to video
        for im in imageList:
            outvid.write(im)

        outvid.release()

    return len(imageList)


def __ffmpegDirect(clip, outputfile, fps, size=[256, 256]):

    vf = clip.shape[0]
    command = ['ffmpeg',
               '-y',  # overwrite output file if it exists
               '-f', 'rawvideo',
               '-s', '%dx%d' % (size[1], size[0]),  # '256x256', # size of one frame
               '-pix_fmt', 'rgb24',
               '-r', '25',  # frames per second
               '-an',  # Tells FFMPEG not to expect any audio
               '-i', '-',  # The input comes from a pipe
               '-vcodec', 'libx264',
               '-b:v', '1500k',
               '-vframes', str(vf),  # 5*25
               '-s', '%dx%d' % (size[1], size[0]),  # '256x256', # size of one frame
               outputfile]

    pipe = sp.Popen(command, stdin=sp.PIPE, stderr=sp.PIPE)
    out, err = pipe.communicate(clip.tostring())
    pipe.wait()
    pipe.terminate()
    return out,err


def createNullVideo(filePath,message="No Image",heightWidth=(100,100)):
    h,w = heightWidth
    imgblank = np.zeros((h,w,3),dtype=np.uint8)
    if message:
        imgblank = cv2.putText(imgblank,message,(h // 2, w // 2),**fontconfig)

    # create blank video with 2 frames
    return writeFramesToVideo([imgblank,imgblank],filePath=filePath,fps=1)
    

def maskedItemRelativeHistogram(img, msk,n_bins=10):
    im = img.copy()
    
    # reduce image to masked portion only 
    for i in range(3):
        im[:,:,i] = (msk == 0) * 0 + (msk > 0) * im[:, :, i]
    
    take_ys= im.sum(axis=2).mean(axis=1) > 0
    take_xs= im.sum(axis=2).mean(axis=0) > 0
    
    imsub=im[take_ys,:,:]
    imsub= imsub[:,take_xs,:]
    
    # determine average vectors for each direction
    h_av = np.mean((imsub == 0) * 0 + (imsub > 0) * imsub,axis=1)
    v_av = np.mean((imsub == 0) * 0 + (imsub > 0) * imsub,axis=0)
    
    #h_abs_vec = np.array(range(h_av.shape[0]))/h_av.shape[0]
    h_ord_vec = h_av.sum(axis=1)/h_av.sum(axis=1).max()
    
    #v_abs_vec = np.array(range(v_av.shape[0]))/v_av.shape[0]
    v_ord_vec = v_av.sum(axis=1)/v_av.sum(axis=1).max()
    
    h_hist=np.histogram(h_ord_vec,bins=n_bins)
    v_hist=np.histogram(v_ord_vec,bins=n_bins)
    
    return (h_hist[0]/h_hist[0].sum(), v_hist[0]/v_hist[0].sum())
    

def drawPoint(im, XY, color=(0,0,255), radius=0, thickness = -1, inplace=False):
    """
        draws a points over the top of an image 
        point : (x,y) 
        color : (R,G,B)
    """
    xy = tuple([round(v) for v in XY])
    if inplace:
        outim = im
    else:
        outim = im.copy()

    outim = cv2.circle(outim, xy, radius=radius, color=color, thickness=thickness)
    return outim


def drawPointList(im, XY_color_list, radius=0, thickness = -1, inplace=False):
    """
        draws points over the top of an image given a list of (point,color) pairs
        point : (x,y) 
        colors : (R,G,B)
    """
    if inplace:
        outim = im
    else:
        outim = im.copy()

    for XY,color in XY_color_list[:-1]:
        xy = tuple([round(v) for v in XY])
        outim = cv2.circle(outim, xy, radius=radius, color=color, thickness=round(thickness * 0.8))
    
    # last point is larger
    XY,color = XY_color_list[-1]
    xy = tuple([round(v) for v in XY])
    outim = cv2.circle(outim, xy, radius=radius, color=color, thickness=round(thickness))
        
    return outim
    
if __name__ == "__main__":
    pass