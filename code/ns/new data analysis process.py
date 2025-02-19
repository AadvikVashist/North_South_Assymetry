import os
import os.path as path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import csv
from PIL import Image, ImageStat
from scipy.optimize import curve_fit
import time
import math
from sklearn.metrics import r2_score
import PIL
class data:   
    def __init__(self, directory, datasetName, shiftDegree , purpose):
        #create all class paths,directories, and variables
        self.createDirectories(directory, datasetName)
        self.createLists(purpose, datasetName)
        self.analysisPrep(shiftDegree)
        #gets purpose condition and executes individual operations based on purpose
        self.conditionals()
    def createDirectories(self, directory, flyby): #create all file directory paths
        #basic datasets
        self.directoryList = directory
        self.flyby = flyby[0]
        self.masterDirectory = self.directoryList["flyby_parent_directory"]
        self.csvFolder = self.directoryList["flyby_data"]
        self.tFolder = os.path.join(self.directoryList["flyby_parent_directory"], self.flyby)
        self.imageFolder =  os.path.join(self.directoryList["flyby_parent_directory"], self.flyby, self.directoryList["flyby_image_directory"])
        #finding files
        try:
            self.csvFile = [os.path.join(self.tFolder, self.csvFolder, file) for file in os.listdir(os.path.join(self.tFolder,self.csvFolder))]
            if len(self.csvFile) == 1:
                self.csvFile = self.csvFile[0]
        except:
            print("no csv file found")
        self.allFiles = [ os.path.join(self.imageFolder,e) for e in os.listdir(self.imageFolder)]
        self.resultsFolder = os.path.join(self.masterDirectory, self.directoryList["analysis_folder"])
        self.flyby_bg_info =  os.path.join(self.masterDirectory,self.directoryList["flyby_info"])
        if len(self.allFiles) != 96:
            print("missing 1+ files")
    def createLists(self, purpose, NSA): #create global variables for data
        self.NSA = []
        self.deviation = []
        self.IF = []
        self.NS = []
        self.lat = []
        self.lon = []
        self.iterations = []
        self.goalNSA  = NSA[1]
        self.errorMargin = NSA[2]
        self.leftCrop = NSA[3][0]
        self.rightCrop = NSA[3][1]
        self.purpose = purpose
        if self.purpose[0] == "tilt":
            self.band = []
        elif self.purpose[0] == "if_sh":
            self.if_sh = []
            self.latSh = []
        self.play = False
    def analysisPrep(self,shiftDegree):
        try:
            self.im = plt.imread(self.allFiles[0])[:,:,0]
        except:
            self.im = plt.imread(self.allFiles[0])[:,:]
        self.height = len(self.im)
        self.width = len(self.im[0])   
        self.im = self.im.astype(np.float32)
        
        if len(self.csvFile) == 2:
            try:
                nans = np.empty((1,self.width))
                nans[:] = np.nan
                if "lat" in self.csvFile[0]:
                    self.lat = np.reshape(np.append((pd.read_csv(self.csvFile[0])), nans, axis = 0), (self.height, self.width))
                    self.lon = np.reshape(np.append((pd.read_csv(self.csvFile[1])), nans, axis = 0), (self.height, self.width))
                else:
                    self.lat = np.reshape(np.append((pd.read_csv(self.csvFile[1])), nans, axis = 0), (self.height, self.width))
                    self.lon = np.reshape(np.append((pd.read_csv(self.csvFile[0])), nans, axis = 0), (self.height, self.width))
            except:
                raise ValueError("error finding csv")    
        else:
            try:
                self.lat = self.Jcube(geo_csv = self.csvFile, var='lat', nL=self.height, nS=self.width)
                self.lon = self.Jcube(geo_csv = self.csvFile, var='lon', nL=self.height, nS=self.width)
                x = 0
            except:
                raise ValueError("error finding csv")     
        self.columnLat = self.lat[:,0]
        temp = self.leftCrop
        if self.leftCrop < 0:
            self.leftCrop = [0,abs(self.rightCrop)]
            self.rightCrop = [abs(temp),self.width]
            self.leftCrop[0] =  min(range(len(self.lon[0, :])), key=lambda x:abs(self.lon[0, x] - self.leftCrop[0]))
            self.rightCrop[0] =  min(range(len(self.lon[0, :])), key=lambda x:abs(self.lon[0, x]-self.rightCrop[0]))
            self.leftCrop[1] =  min(range(len(self.lon[0, :])), key=lambda x:abs(self.lon[0, x] - self.leftCrop[1]))
            self.rightCrop[1] =  min(range(len(self.lon[0, :])), key=lambda x:abs(self.lon[0, x]-self.rightCrop[1]))
        else:
            self.leftCrop =  min(range(len(self.lon[0, :])), key=lambda x:abs(self.lon[0, x] - self.leftCrop))
            self.rightCrop =  min(range(len(self.lon[0, :])), key=lambda x:abs(self.lon[0, x]-self.rightCrop))
        if "Ti" in self.flyby:
            self.subset = tuple([(self.columnLat > self.goalNSA -30) & (self.columnLat < self.goalNSA + 30.0)])
        else:
            self.subset = tuple([(self.columnLat > self.goalNSA -15) & (self.columnLat < self.goalNSA + 15.0)])
        self.lat_sh = self.columnLat[self.subset] ## subset HC band b/t 30°S to 0°N 
        self.lon_sh = self.lon[self.subset]
        latRange = np.nanmax(self.lat)-np.nanmin(self.lat)
        latTicks = len(self.lat)/latRange
        self.shiftDegree=shiftDegree
        self.num_of_nans = int(latTicks*shiftDegree)
        self.nans = [np.nan]*(self.num_of_nans)
        if self.purpose[0] == "if_sh":
            self.ifSubset = tuple([(self.columnLat > -90.0) & (self.columnLat < 90.0)])
    def createFolder(self, folderPath = None):
        if not folderPath:
            folderPath = os.path.join(self.masterDirectory,self.directoryList["analysis_folder"])
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
        self.resultsFolder = folderPath
    def createFile(self):
        open(self.resultsFolder + self.flyby + "_analytics.csv","w")
        x = open(self.resultsFolder + self.flyby + "_analytics.csv","a+", newline='')
        self.analysisFile = x
    def fileWrite(self, x):
        a = csv.writer(self.analysisFile)
        a.writerow(x)
    def fileClose(self):
        self.analysisFile.close()
    def averages(self, x):
        X = []
        for i in range(len(x)):
            X.append(np.mean(x[i]))
        return X
    def Jcube(self, nL, nS, csv=None, geo_csv=None, bands=None, var=None): #Get image to create arrays that help read image data as latitude data
        '''Converts any Jcube or geocube csv file to numpy 2D array
        Note: Requires pandas and numpy.
        
        Parameters
        ----------
        csv: str
            Name of Jcube csv file with raw I/F data 
        geo_csv: str
            Name of csv file from geocubes with geographic info on a VIMS cube (.cub) 
            Can include relative directory location (e.g. 'some_dir/test.csv')
        nL: int
            number of lines or y-dimension of VIMS cube
        nS: int
            number of samples or x-dimension of VIMS cube
        vars: str
            geo_cube parameters that include "I/F", lat", "lon", "lat_res", "lon_res", 
            "phase", "inc", "eme", and "azimuth"
        '''
        ## check var is the correct string
        if var not in ["lat", "lon", "lat_res", "lon_res", "phase", "inc", "eme", "azimuth"] and var is not None:
            raise ValueError("Variable string ('var') is not formatted as one of the following options: \n"+\
                            '"I/F", "lat", "lon", "lat_res", "lon_res", "phase", "inc", "eme", "azimuth"')
        ## create image of Titan
        if geo_csv is None:
            ## read csv; can include relative directory
            csv = pd.read_csv(csv, header=None)
        
            def getMeanImg(csv, bands, nL, nS):
                '''Get the mean I/F image for a set of wavelengths from a Jcube csv file
                Note: a single 'bands' value will return the image at that wavelength.
                
                Parameters
                ----------
                csv: str 
                    name of csv file for VIMS cube
                bands: int or list of int 
                    band values from 96-352 for near-infrared VIMS windows
                nL: int
                    number of lines 
                nS: int
                    number of samples
                '''
                if isinstance(bands, int):
                    bands = [bands]
                img = []
                for band in bands:
                    cube = np.array(csv)[:,band].reshape(nL,nS)
                    cube[cube < -1e3] = 0
                    img.append(cube)#[band, :, :])
                return np.nanmean(img, axis=0)
            return getMeanImg(csv=csv, bands=bands, nL=nL, nS=nS)
        ## create geocube 
        if csv is None:
            ## read csv; can include relative directory
            geo = pd.read_csv(geo_csv, header=None)
            ## output chosen variable 2D array
            if var == 'lat':
                return np.array(geo)[:,0].reshape(nL,nS)
            if var == 'lon':
                return np.array(geo)[:,1].reshape(nL,nS)
            if var == 'lat_res':
                return np.array(geo)[:,2].reshape(nL,nS)
            if var == 'lon_res':
                return np.array(geo)[:,3].reshape(nL,nS)
            if var == 'phase':
                return np.array(geo)[:,4].reshape(nL,nS)
            if var == 'inc':
                return np.array(geo)[:,5].reshape(nL,nS)
            if var == 'eme':
                return np.array(geo)[:,6].reshape(nL,nS)
            if var == 'azimuth':
                return np.array(geo)[:,7].reshape(nL,nS)
        ## create geocube 
        if csv is None:
            ## read csv; can include relative directory
            geo = pd.read_csv(geo_csv, header=None)
            return (np.array(geo)[:,0].reshape(nL,nS), np.array(geo)[:,1].reshape(nL,nS))
    def brightness(self, im_file ):
        im = Image.open(im_file).convert('L')
        stat = ImageStat.Stat(im)
        return stat.mean[0]
    def polyfit(self, x, y, degree): #alternate fit for polynomials
        results = {}
        coeffs = np.polyfit(x, y, degree)
        p = np.poly1d(coeffs)
        #calculate r-squared
        yhat = p(x)
        ybar = np.sum(y)/len(y)
        ssreg = np.sum((yhat-ybar)**2)
        sstot = np.sum((y - ybar)**2)
        return ssreg / sstot
    def gaussian(self, x, amplitude, mean, stddev): #gaussian fit
        return amplitude * np.exp(-((x - mean) / 4 / stddev)**2)
    def poly6(self, x, g, h, i, j, a, b, c): #sextic function
        return g*x**6+h*x**5+i*x**4+j*x**3+a*x**2+b*x+c
    def poly6Prime(self, x, g, h, i, j, a, b, c): #derivative of sextic function
        return 6*g*x**5+5*h*x**4+4*i*x**3+3*j*x**2+2*a*x+b
    def poly6Derivative(self, g, h, i, j, a, b, c): #derivative of sextic function coefficents
        return [6*g,5*h,4*i,3*j,2*a,b]
    def running_mean(self, x, N): #window avearage
        return np.convolve(x, np.ones(N)/N, mode='valid')
    def conditionals(self):
        print("purpose is", self.purpose[0])
        if self.purpose[0] == "data":
            self.getDataControl()
        elif self.purpose[0] == "tilt":
            self.getTiltControl()
        elif self.purpose[0] == "if_sh":
            self.getIf_shControl()
        else:
            print("data output type not understood; ", self.purpose[0], " not valid")
    def getDataControl(self): #iteration over images within flyby
        for self.iter in range(len(self.allFiles)):
            self.a = time.time()
            self.currentFile = self.allFiles[self.iter]
            self.iterations.append(self.iter)
            self.dataAnalysis()
            print("dataset", self.flyby, "     image", "%02d" % (self.iter),"     boundary",format(self.NSA[self.iter],'.15f') ,"      deviation", format(self.deviation[self.iter],'.15f'), "        N/S",format(self.NS[self.iter],'.10f') )
        #write data
        if "write" in self.purpose[1]:
            #create folder and file
            self.createFolder()
            self.createFile()
            try:
                datasetAverage = self.averages([self.NSA, np.std(self.NSA), self.NS])
                self.NSA.append(datasetAverage[0]); self.deviation.append(datasetAverage[1]); self.NS.append(datasetAverage[2]); self.iterations.append(self.flyby)
                self.NSA.insert(0, "NSA"); self.deviation.insert(0, "Deviation"); self.NS.insert(0,"N/S"); self.iterations.insert(0, "File Number")
                self.fileWrite(self.NSA)
                self.fileWrite(self.deviation)
                self.fileWrite(self.NS)
                self.fileWrite(self.iterations)
            finally:
                self.fileClose()
    def getIf_shControl(self):
        if len(self.purpose[1]) == 0:
            for self.iter in range(len(self.allFiles)):
                self.currentFile = self.allFiles[self.iter]
                self.iterations.append(self.iter)
                self.ifAnalysis()
        else:
            for self.iter in range(len(self.allFiles)):
                if self.iter in self.purpose[1]:
                    self.currentFile = self.allFiles[self.iter]
                    self.iterations.append(self.iter)
                    self.if_sh.append(self.ifAnalysis())
    def getTiltControl(self):
        #go through each file
        for self.iter in range(len(self.allFiles)):
            self.currentFile = self.allFiles[self.iter]
            if self.iter in self.purpose[1]:
                self.tiltAnalysis()
        #write data
            #print(self.band)
            pass
    def visualizeBrightnessDifferenceSamplingArea(self, im, x, nsaLat):
        if type(self.leftCrop) is list:
            im[x[0]:x[1],self.rightCrop[0]:self.leftCrop[0]] *= 2
            im[(x[1]+1):x[2],self.rightCrop[0]:self.leftCrop[0]] *=  0.5
            im[x[0]:x[1],self.rightCrop[1]:self.leftCrop[1]] *= 2
            im[(x[1]+1):x[2],self.rightCrop[1]:self.leftCrop[1]] *=  0.5
        else:
            im[x[0]:x[1],self.leftCrop:self.rightCrop] *= 2
            im[(x[1]+1):x[2],self.leftCrop:self.rightCrop] *=  0.5
        plt.imshow(im, cmap = 'Greys')
        plt.show()
    def brightnessDifference(self, im, nsaLat):
        splitY = min(range(len(self.lat[:, 0])), key=lambda x:abs(self.lat[x,0]-nsaLat))
        horizontalSample= 4
        verticalSample = 30
        northSplit = min(range(len(self.lat[:, 0])), key=lambda x:abs(self.lat[x,0]-verticalSample-nsaLat))
        southSplit = min(range(len(self.lat[:, 0])), key=lambda x:abs(self.lat[x,0]+verticalSample-nsaLat))
        
        if type(self.leftCrop) is list:
            north = im[northSplit:splitY,self.rightCrop[0]:self.leftCrop[0]]
            south = im[(splitY+1):southSplit,self.rightCrop[0]:self.leftCrop[0]]
            north = np.concatenate((north, im[northSplit:splitY,self.rightCrop[1]:self.leftCrop[1]]), axis = 1)
            south = np.concatenate((south,im[(splitY+1):southSplit,self.rightCrop[1]:self.leftCrop[1]]), axis = 1)
        else:
            if self.leftCrop > self.rightCrop:
                north = im[northSplit:splitY,self.rightCrop:self.leftCrop]
                south = im[(splitY+1):southSplit,self.rightCrop:self.leftCrop]
            else:
                north = im[northSplit:splitY,self.leftCrop:self.rightCrop]
                south = im[(splitY+1):southSplit,self.leftCrop:self.rightCrop]
        northM = np.mean(north[north != 0.])
        southM = np.mean(south[south != 0.])
        return northM/southM
    def dataAnalysis(self):
        try: #open image arrays
            self.im = plt.imread(self.currentFile)[:,:,0]
        except:
            self.im = plt.imread(self.currentFile)[:,:]
        self.im = self.im.astype(np.int16)
        hc_band = np.empty((self.height, self.width), float)
        nsa_lats = []; nsa_lons = []; cols = []
        latRange = np.max(self.lat)-np.min(self.lat)
        latTicks = len(self.lat)/latRange
        #get latitude values of each pixel using CSV
        width = []
        subtraction = (np.insert(self.im, 0, np.array(self.num_of_nans*[[0]*self.width]), axis = 0) - np.concatenate((self.im,self.num_of_nans*[[0]*self.width])))
        hc_band = subtraction[int(np.round(self.num_of_nans/2, 0)):-1*int(np.round(self.num_of_nans/2, 0))]
        if True:
            self.createFolder(os.path.join(self.masterDirectory,self.flyby,"hc_band"))
            self.convert_array_to_image(hc_band, os.path.join(self.masterDirectory,self.flyby,"hc_band", (os.path.splitext(os.path.relpath(self.currentFile,os.path.join(self.masterDirectory,self.flyby,self.directoryList["flyby_image_directory"])))[0] +  "_band")))
        if_sh = hc_band[self.subset]
        lon_subset = []
        if type(self.leftCrop) is list:
            a =  sorted((self.rightCrop[0],self.leftCrop[0]))
            b =  sorted((self.rightCrop[1],self.leftCrop[1]))
            lon_subset = np.concatenate((range(*a), range(*b)))
        else:
            if self.leftCrop > self.rightCrop:
                lon_subset = range(self.rightCrop,self.leftCrop)
            else:
                lon_subset = range(self.leftCrop,self.rightCrop)
        for col in range(self.width):
            if col in lon_subset:
                columnHC = hc_band[:,col]
                if_sh = columnHC[self.subset] ## subset HC band b/t 30°S to 0°N 
                if np.min(if_sh) != np.max(if_sh):
                    try:
                        popt, _ = curve_fit(self.poly6, self.lat_sh, if_sh)#apply sextic regression to data
                        poptD = self.poly6Derivative(*popt)#get derivative of sextic regression
                        derivativeRoot = np.roots(poptD) #roots (Real and imaginary) of derivative function
                        realDerivativeRoots = derivativeRoot[np.isreal(derivativeRoot)] #remove extraneous soulutions (imaginary)
                        drIndex = min(range(len(realDerivativeRoots)), key=lambda x: abs(realDerivativeRoots[x]-self.goalNSA)) #find value closest to NSA
                        derivativeRoots = realDerivativeRoots[drIndex]
                        if abs(derivativeRoots.real-self.goalNSA) >= self.errorMargin:
                            width.append(False)
                        else: 
                            nsa_lats.append(derivativeRoots.real)
                            width.append(True)
                    except:
                        width.append(False)
            else:
                width.append(False)
        self.NSA_Analysis(nsa_lats, self.im,width)
        print(time.time() - self.a)
    def ifAnalysis(self):
        #open image arrays
        try:
            self.im = plt.imread(self.currentFile)[:,:,0]
        except:
            self.im = plt.imread(self.currentFile)[:,:]
        self.im = self.im.astype(np.float32)
        self.hc_band = np.empty((self.height, self.width), float)
        #get latitude values of each pixel using CSV
        count = 0
        non_zero = np.array(np.any(self.im != 0,axis=1))
        image = self.im[non_zero, :]
        crop = self.im[non_zero, :]
        ab = self.lat[non_zero,0]
        Result = image[:,~np.any(crop == 0, axis = 0)]
        try:
            b = Result[int(len(Result)*0.25):int(len(Result)*0.75), int(len(Result[0])*0.25):int(len(Result[0])*0.75)]
        except:
            try:
                self.im = plt.imread(self.currentFile)[:,:,0]
            except:
                self.im = plt.imread(self.currentFile)[:,:]
            b = 0
        b = np.mean(b)*10
        a = np.mean(Result, axis = 1)
        ab = ab[abs(a)<abs(b)]
        a = a[abs(a)<abs(b)]
        return [ab, a]
    def smooth(self, y, box_pts):
        box = np.ones(box_pts)/box_pts
        y_smooth = np.convolve(y, box, mode='same')
        return y_smooth
    def tiltAnalysis(self):
        #open image arrays
        if self.iter in self.purpose[1]:
            try:
                self.im = plt.imread(self.currentFile)[:,:,0]
            except:
                self.im = plt.imread(self.currentFile)[:,:]
            self.im = self.im.astype(np.float32)
            self.hc_band = np.empty((self.height, self.width), float)
            nsa_lats = []; nsa_lons = []; cols = []
            columns = []
            lon_shTilt = []
            for col in self.purpose[2]:
                x = self.columnAnalysis(col)
                if x != None:
                    nsa_lats.append(x)
                    lon_shTilt.append(self.lon[0,col])
                    columns.append(col)
                
            self.band.append([columns, lon_shTilt, self.smooth(nsa_lats,self.purpose[4])])
    def linearRegress(self, x, y):
        return np.polyfit(x,y,1)
    def angle(self, slope):
        return 180/math.pi*np.arctan(slope)
    def NSATilt(self, x, y):
        function = self.linearRegress(x,y)
        x=np.array(x, dtype = "float64")
        ys =  x*function[0]+function[1]
        a = r2_score(y, ys)
        return function, self.angle(function[0]), a
    def if_sh_data(self, column):
        subtraction = (np.insert(self.im[:,column], [0]*self.num_of_nans, self.nans) - np.concatenate((self.im[:,column], self.nans)))
        self.hc_band[:,column] = subtraction[int(self.num_of_nans/2):int(-self.num_of_nans/2)]
        #hc_band[crop[0]:crop[1],crop[2]:crop[3]]
        columnHC = self.hc_band[:,column]
        if_sh = columnHC ## subset HC band b/t 30°S to 0°N 
        #lat_sh = self.columnLat[self.subset]  ## subset HC band b/t 30°S to 0°N 
        #lon_sh = self.lon[:,column][self.subset]  ## subset HC band b/t 30°S to 0°N 
        return if_sh
    def NSA_Analysis(self, im_nsa_lat,image, x):
        dev = np.std(im_nsa_lat) #standard deviation
        average = np.nanmean(im_nsa_lat) #standard average
        combo = 4
        movingAverageList = self.running_mean(im_nsa_lat, combo) #moving average
        # if "showAverage" in self.purpose[1]:
        #     plt.plot(range(len(movingAverageList)),movingAverageList)
        #     plt.show()
        movingAvg = np.mean(movingAverageList) #moving average
        diff = self.brightnessDifference(image, movingAvg) #difference between north and south
        self.NSA.append(movingAvg)
        self.deviation.append(dev)
        self.NS.append(diff)
    def columnAnalysis(self,column):
        subtraction = (np.insert(self.im[:,column], [0]*self.num_of_nans, self.nans) - np.concatenate((self.im[:,column], self.nans)))
        self.hc_band[:,column] = subtraction[int(self.num_of_nans/2):int(-self.num_of_nans/2)]
        #hc_band[crop[0]:crop[1],crop[2]:crop[3]]
        columnHC = self.hc_band[:,column]
        if_sh = columnHC[self.subset] ## subset HC band b/t 30°S to 0°N 
        #lat_sh = self.columnLat[self.subset]  ## subset HC band b/t 30°S to 0°N 
        self.lon_sh = self.lon[:,column][self.subset]  ## subset HC band b/t 30°S to 0°N 
        
        try:
            popt, _ = curve_fit(self.poly6, self.lat_sh, if_sh)#apply sextic regression to data
            poptD = self.poly6Derivative(*popt)#get derivative of sextic regression
            derivativeRoot = np.roots(poptD) #roots (Real and imaginary) of derivative function
            derivativeRoots = derivativeRoot[np.isreal(derivativeRoot)] #remove extraneous soulutions (imaginary)
            drIndex = min(range(len(derivativeRoots)), key=lambda x: abs(derivativeRoots[x]-self.goalNSA)) #find value closest to NSA
            derivativeRoots = derivativeRoots[drIndex] #get lat of derivative root
            derivativeRoots.real #append to nsa_lats
            return derivativeRoots.real
        except:
            return None
    def convert_array_to_image(self, array, savename):
        if array is not np.array:
            array = np.array(array, dtype=np.float32)
        else:
            array.astype(np.uint8)
        quintiles = np.quantile(array,np.arange(0,1.01,0.01))
        # quintile_range = [quintiles[i]-quintiles[i-1] for i in range(4,len(quintiles-3))]
        # min = 0
        # max = 0
    
        min = quintiles[15]
        max = quintiles[-16]
        
        
        # plt.imshow(array)
        # plt.show()
        if min != 0:
            array -= min
        max = max-min
        array = np.clip(array, 0, max)
        ranges = np.ptp(array)
        if ranges != 255:
            array *= 255 / ranges
        array.astype(np.int8)
        im = PIL.Image.fromarray(array)
        im = im.convert("L")
        im.save(savename+ ".png")