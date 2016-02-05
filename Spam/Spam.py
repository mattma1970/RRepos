import unicodecsv as unicsv
import numpy as np
import pandas as pd
import re
import os # misc OS functions
import random as rand
import math
import itertools

# Naive Bayes classifier


## Globals
data_path="./Messages"
CONST_MIN_HEADER_SIZE=10
DEBUG=True
DEBUG_ATTACHMENTS=True
MAX_WORD_LENGTH=20   # used to remove stray long words that are unlikely to be english words




# TODO: Find python package for text preprocessing.
# preprocessing methods and word extraction from a single email.
class TextProcessor:
    def __init__(self):
        self.getStopWords()

    # Properties ##################
    dfEmails = pd.DataFrame(columns=('header','body'))     # hold the data being processed
    _rxIllegalChars = "[^a-zA-Z0-9\s]" #Regular expression patterns for admissible characters to be replaced with blanks
    _stopWords = np.array(None)

    _blIsSpam = False    # used to tag an email as either spam or ham

    def setTag(self,blIsSpam):
        self._blIsSpam = blIsSpam
    
    # Class methods ################
    def getStopWords(self):
        self._stopWords = np.genfromtxt('common-english-words.txt',dtype=str, delimiter=',')
        
    # set all body text to lower case
    def toLower(self):
        for i,myRow in self.dfEmails.iterrows():
            #myrow[0]=index value NOT row number; myrow[1]=header myrow[2]=body
            liNewLowerLines = map(lambda x: x.lower(),myRow['body'])
            self.dfEmails['body'][i]=liNewLowerLines
    
    #remove punctuation and other XML chars.
    def removePunc(self):
        for i,myRow in self.dfEmails.iterrows():
            liNewLines = [re.sub(self._rxIllegalChars,' ',line) for line in myRow['body']]
            self.dfEmails['body'][i]=liNewLines
    
    #basic stemming. Remove ed,ing, ly
    #operates on dfEmail in place
    #assumes punctuation removed.
    def stem(self):
        rxED = '(ed)[\s\b]'
        rxING = '(ing)[\s\b]'
        rxLY = '(ly)[\s\b]'

        for i,myRow in self.dfEmails.iterrows():
                liNewLines = [re.sub(rxED,' ',line) for line in myRow['body']]
                liNewLines = [re.sub(rxING,' ',line) for line in liNewLines]
                liNewLines = [re.sub(rxLY,' ',line) for line in liNewLines]
                self.dfEmails['body'][i]=liNewLines        
    
    #get a list of unique words occuring in a single email.
    # remove stop words
    #returns dataframe rows=email,columns=uniquewords, isSpam boolean
    def getUniqueWordsAndTag(self,maxLength=100):
        liUniqueWords = []
        for i,myRow in self.dfEmails.iterrows():
            setWords = set()
            for line in myRow['body']:
                for word in line.split(' '):
                    if len(word)>1 and word!=' ' and  not (word in self._stopWords) and len(word)<maxLength:
                        setWords.add(word)  #takes care of only adding unique words
            liUniqueWords.append({'words':setWords,'isSpam':self._blIsSpam})
        return pd.DataFrame(liUniqueWords)



# class container helper functions that operate collections of emails.
# Email data should be of one type only (ie.e either ham or spam)
class Emails:
    def __init(self):
        pass

    liEmails = []  # holds the list of email texts.
    dfSplitEmails = pd.DataFrame(columns=('header','body'))# hold the header and body when seperated
    isSpam = False  #flag indicating if spam or not. Applied to all emails in dfSplitEmails.
    
    # Import emails
    # helper functions for file loading
    def blIsValid(self,strName):
        # Check that the file name conforms to the style we want.
        invalidChars = re.compile('[^\.0-9abcdef]')
        validFormat = re.compile('^\d{4,5}\.[0-9a-f]{10,}')
        if invalidChars.match(strName) is None and validFormat.match(strName):
            return True
        else:
            return False
        
    def getAllMessageFileNames(self,path='./Messages'):
        # recursively walk the message directory tree and get the fully qualified list of files.
        # return a dictionary with key=subdirectory name, 
        #      value is pandas DataFrame of unqualified file names (FQName) and unqualifies name 'Name')
        dicFileNames = {}
        pwd = os.getcwd()
        # if relative path specified get the the fully qualified name
        pwd = os.path.join(pwd,'Messages')
        if path=='./Messages':
            dirNames = os.listdir(pwd)    # get directories in the current dir.
        else:
            dirNames = [path]           #else we have been passed a child directory
            
        for dirName in dirNames:
            listFileNames = []
            listFQFileNames = []
            # compile list of names
            for fn in os.listdir(os.path.join(pwd,dirName)):
                if self.blIsValid(fn):  # targetin
                    listFQFileNames.append(os.path.join(pwd,dirName,fn))
                    listFileNames.append(fn)
            #convert to pandas dataframe
            df=pd.DataFrame({'FQNames':listFQFileNames,'Names':listFileNames})
            df=df.sort('Names')
            dicFileNames[dirName] = df
        return (dicFileNames)    
    
    # List the directories and file counts in each folder.
    def showMessageCounts(self,allFiles_dic):
        allFiles_dic = self.getAllMessageFileNames()
        for key in allFiles_dic.keys():
            print "dir={} file={}".format(key,len(allFiles_dic[key]['Names']))    

    def loadEmails(self,liFullDirectoryListing,liFileLocations=[]):
        # get some or all emails from the full list and return list of lists of email lines of text
        liEmails=[] #list of lists of text lines from each email
        if len(liFileLocations)>0:
            for i in liFileLocations:
                #print liFullDirectoryListing['FQNames'].iloc[i]
                f=open(liFullDirectoryListing['FQNames'].iloc[i])
                lines=f.readlines()
                f.close()
                liEmails.append(map(lambda s: s.replace('\n',''),lines))
        else:
            for i,myRow in liFullDirectoryListing.iterrows():
                f=open(myRow['FQNames'])
                lines=f.readlines()
                f.close()
                liEmails.append(map(lambda s: s.replace('\n',''),lines))            
        return liEmails   
   
    # Get the boundary string from headers in dfSplitEmails (via content-type key)
    # return a list of tuples containing rownumber and boundary string where attachment is present)
    def getBoundaryStrings(self):
        liBoundaryKeys = []
        reContentKey = re.compile('^(content-type)\s*:\s*([A-Za-z\/]+);',re.I)
        reBoundaryKey = re.compile('.*(boundary)\s*=\s*([^;]*);?.*',re.I)
        for i,myRow in self.dfSplitEmails.iterrows(): # get index and row (series) seperately
            blHasAttachment=False
            strBoundaryKey=''
            try:
                for item in myRow['header']:
                    mContentKey = reContentKey.match(item)
                    mBoundaryKey = reBoundaryKey.match(item)
                    if mContentKey and "multi" in mContentKey.group(2).lower():
                        blHasAttachment=True
                    if mBoundaryKey:  
                        strBoundaryKey=mBoundaryKey.group(2).strip('" ')
            except:
                print "problem at i={}".format(i)
            if blHasAttachment:
                liBoundaryKeys.append([i,strBoundaryKey])
        return liBoundaryKeys
                
    
    # Find the location of all occurances of the boundary string (from Content-Type key)
    # The number of occurences will be used as validation that matching pairs of boundary strings are present.
    def getBoundaryStringLocs(self,liBStrings):
        #loop through the emails that have attachments and get the line numbers where the boundary string appear.
        # note there should be an odd number of locations as the boundaries should appear in pairs plus there should be one the # #marks the start of the email
        # Returns a list of list tuples [Df index, [start locations],[end locations]]
        liLocations=[]
        for row in liBStrings:
            intLineCounter=0
            liStartBoundaryLocs = []
            liEndBoundaryLocs = []
            # start markers are preceeded by two -'s. Closing ones are preceeded and followed by two dashes.
            rxStartBoundary = re.compile("-{2}"+row[1])
            rxEndBoundary = re.compile("-{2}"+row[1]+"-{2}")
            for line in self.dfSplitEmails.loc[row[0]]['body']:
                if rxEndBoundary.search(line)!=None:
                    liEndBoundaryLocs.append(intLineCounter)   
                elif rxStartBoundary.search(line)!=None: 
                    liStartBoundaryLocs.append(intLineCounter)                    
                intLineCounter+=1
            liLocations.append([row[0],liStartBoundaryLocs,liEndBoundaryLocs])
        return liLocations

    #Remove the attachments that may be embedded in the body of the email.
    # Attachments marked by boundary strings.
    # operates on dfSplitEmails in place.
    # no return value
    def removeAttachments(self,liBoundaries):
        # @liBoundaries - list of tuples of lists. [ iloc in df,[list of start locations],[list of end loc]
        liEmailsToRemove = [] # iloc of emails to remove from dfSplitEmails.
        liTempEmails = []
        #print self.dfSplitEmails.head()
        for row in liBoundaries:
            # check that the pairing of the start end/markers make sense.
            # i.e there is an opening, a start and a closing occurence of the boundary string. 
            # If not, then the email should be discarded as we can't be sure the content is body of the email we care about. 
            if len(row[1])>=2 and len(row[2])>=1:
                intAttachStartLoc = row[1][1]
                intAttachEndLoc = row[2][-1]
                ##Learning: iLoc etc are select statements that create new objects and hence changes to new objects dont' propogate.
                ##Access object contents vi (reversed) indexation df[column][row index]
                ##Alternatively could use .xs method and set copy=False to prevent copy being created.
                del self.dfSplitEmails['body'][row[0]][intAttachStartLoc:(intAttachEndLoc+1)]
                del self.dfSplitEmails['body'][row[0]][row[1][0]]
            else:
                self.dfSplitEmails['body'][row[0]]=[] # delete the email. TODO ensure that empty emails are not included in further analysis.
                self.dfSplitEmails['header'][row[0]]=[]
                
            
    
    # Locate and remove attachments
    # Return a list of emails that should be dropped due to mismatched boundary strings.
    # Management function for removing attachements.
    def dealWithAttachments(self):
        liBStrings= self.getBoundaryStrings()
        liBStringLocs = self.getBoundaryStringLocs(liBStrings)
        self.removeAttachments(liBStringLocs) 
        if DEBUG_ATTACHMENTS:
            print "Locating remaining boundary tags"
            for i,myRow in self.dfSplitEmails.iterrows():
                for lines in myRow['body']:
                    if 'boundary' in lines.lower():
                        print "index {}, {} ".format(i,lines)
            print "End locating boundary tags"
            
    def _severHeader(self,liText):
        # Get the seperator for header of a single email.
        # @liText is the lines of text for a single email.
        # Return a dictionary of two lists. The first containing the Header Lines list and the second containing the body lines list.
        loc = -1
        try:
            loc = liText.index('')
        except:
            pass
        if loc!=-1 and loc>CONST_MIN_HEADER_SIZE: # if no split then throw the record away as its unusable
            return ({'header':list(liText[0:loc]),'body':list(liText[loc+1:len(liText)])})
        else:
            return ({'header':[],'body':[]})

    def severHeaders(self):
        # liEmails is a list of list of email text lines.
        # sets pdSplitEmails, a dataframe with cols header and body and blIsSpam flag
        liSplitEmails = map(self._severHeader,self.liEmails)
        self.dfSplitEmails = pd.DataFrame(liSplitEmails)



# Class represents the Naive Bayes filter singleton.
class NaiveBayesFilter:
    def __init(self):
        pass
    
    #All emails pre-processed and ready for inputing into training alg,.
    _dfPreprocessedEmails = pd.DataFrame(columns=('words','isSpam'))
    
    #probability tables.
    dfProb = pd.DataFrame(columns=('words','pPresSpam','pPresHam','pAbsSpam','pAbsHam'))
    liBOW = [] #Bag of words. A list of unique words in the whole corpus. A feature vector is a vector with one coordinate per  bow word.
    
    #The threshold for the LLR below which an email is considered spam.
    dThreshold = 0.0
    
    #totals
    _intTotalSpamEmails = 0
    _intTotalHamEmails = 0
    
 

    #Load get all the emails in the ./Message directory.
    #Deal with each Dir one at a time and tag emails as ham/spam
    #directoryList - list of relative directory names and correspondig tag isSpam.
    # indx a list of index labels to select emails to work with.
    def importParseCorpus(self, directoryList, indx=[]):
        liEmailDFs = [] # a list used to accumulate directories of emails before concatinating them.
        i =0
        for strDir in directoryList['dir']:
            eEmails = Emails()
            if DEBUG:
                print ("start load {}".format(strDir))
            #get file names in the current directory.
            allFiles_dic = eEmails.getAllMessageFileNames(directoryList['dir'][i])
            #eEmails.showMessageCounts(allFiles_dic)            

            # get the sample emails from easy_ham folder
            if len(indx)>0:
                eEmails.liEmails = eEmails.loadEmails(allFiles_dic[directoryList['dir'][i]],indx)
            else:
                eEmails.liEmails = eEmails.loadEmails(allFiles_dic[directoryList['dir'][i]])
                
            blIsSpam = directoryList['isSpam'][i]
            
            # split header and body using the blank line delimiter that seperates them
            eEmails.severHeaders()
            #remove attachments from the bodies. Find the Content-Type key in the header, 
            eEmails.dealWithAttachments()
            #text pre-precessing 
            Tp = TextProcessor()
            Tp.dfEmails = eEmails.dfSplitEmails
            Tp.setTag(blIsSpam)  
            Tp.toLower()
            Tp.removePunc()
            Tp.stem()
            #Extract the unique words from emails. Create a list of words for each email.
            dfWords = Tp.getUniqueWordsAndTag()
            #print len(dfWords)
            liEmailDFs.append(Tp.getUniqueWordsAndTag(MAX_WORD_LENGTH)) ## add to df list until finished importing all emails.
            i+=1
            emailsAdded = len(liEmailDFs[-1])
            if blIsSpam:
                self._intTotalSpamEmails+=emailsAdded
            else:
                self._intTotalHamEmails+=emailsAdded
                
            if DEBUG:
                print "End loading {}. Emails processed {}".format(strDir,emailsAdded)
              
                       
        self._dfPreprocessedEmails = pd.concat(liEmailDFs)
        #print len(self._dfPreprocessedEmails)
        
    # calculate the dfProbability table based on the training data passed int.
    # flTrainingPercent is floating point value representing the portion of preprocessed data use for training. 
    # The balance to be used for testing. 
    # Returns a list of row numbers for _dfPreprocessed emails.
    def splitCorpus(self, flTrainingPercent):
     #Split the preprocessed data into training and test emails. 
        rand.seed(418910)
        totalEmails=self._intTotalSpamEmails+self._intTotalHamEmails
        trainHamIdx = rand.sample(range(0,self._intTotalHamEmails),int(math.floor(self._intTotalHamEmails*flTrainingPercent)))
        trainSpamIdx = rand.sample(range(self._intTotalHamEmails,totalEmails),int(math.floor(self._intTotalSpamEmails*flTrainingPercent)))

        trainIdx = trainHamIdx+trainSpamIdx
        setTestIdx= set(range(0,totalEmails))
        setTrainIdx = set(trainIdx)
        setTestIdx = setTestIdx-setTrainIdx
        testIdx = list(setTestIdx)

        if DEBUG:
            print "Length of training set {}: Length of test set {}".format(len(trainIdx),len(testIdx))
        
        return trainIdx,testIdx
    
    
          
         
         
    def trainFilter(self,trainIdx):
        # Method to create conditional probabilities tables for training data.
        # @trainIdx is a list of row numbers in dfPreprocessedEmails included inthe training set. 
        row = 0
        liUnlistedWords = [] # list of tuples (word from an email, isSpam bool)
        #unlist self.dfPreprocessedEmails which has rows structure of set of unique words,isspam bool
        dfTrainingSet = self._dfPreprocessedEmails.iloc[trainIdx]
        for i,anEmail in dfTrainingSet.iterrows():
            liWords=list(anEmail['words'])
            liFlag = list(itertools.repeat(anEmail['isSpam'],len(liWords)))
            liUnlistedWords[0:0]=zip(liWords,liFlag)

        
        # group by word to be able access the isspam counts.
        dfUnlistedWords = pd.DataFrame(liUnlistedWords,columns=('words','isSpam')).groupby(('words','isSpam')).count()
        if DEBUG:
            print dfUnlistedWords.head()
            print dfUnlistedWords.tail()
            print dfUnlistedWords['isSpam']['yes'] # smaple accessor
            
        #get total spam and ham counts
        intTotalSpamEmails= float(sum(dfTrainingSet['isSpam']))
        intTotalHamEmails = float(len(dfTrainingSet)-intTotalSpamEmails)
        
        liProbTables = [] #list of dictionaries to convert to df
        for word in self.liBOW:
            probPresSpam=0.0
            probPresHam=0.0
            try:
                probPresSpam =float(dfUnlistedWords['isSpam'][word][True])/intTotalSpamEmails
            except:
                pass
            
            try:
                probPresHam = float(dfUnlistedWords['isSpam'][word][False])/intTotalHamEmails
            except:
                pass
            
            liProbTables.append((word,probPresSpam,probPresHam,1.0-probPresSpam,1.0-probPresHam))
            
        
        ret= pd.DataFrame(liProbTables,columns=('word','pPresSpam','pPresHam','pAbsSpam','pAbsHam'))
        ret.set_index(ret['word'])
        self.dfProb=ret
        return ret
        
            

    #calculate precision and recall
    def evaluatePerformance(self, dfTest):
        pass

    #plot the recall performance vs threshold for range of thresholds
    def plotPerformance(self,dfTest,dStartThresh,dfEndThresh):
        pass
    
    # Get bag of words.
    #if list specified then only process those row numbers (iloc)
    def createBOW(self,liIndecies=[]):
        #loop over _drPreprocessedEmails and get one consolidated list of unique words.
        setWords = set()
        if len(liIndecies)==0:
            for i,myRow in self._dfPreprocessedEmails.iterrows():
                if len(setWords)==0:
                    setWords = myRow['words']
                else:
                    setWords=setWords.union(myRow['words'])
                #print len(setWords)
        else:
            for i in liIndecies:
                if len(setWords)==0:
                    setWords=self._dfPreprocessedEmails.iloc[i]['words']
                else:
                    setWords=setWords.union(self._dfPreprocessedEmails.iloc[i]['words'])
                    
        self.liBOW=list(setWords)
        if DEBUG:
            print "BOW: Length of BOW {}".format(len(self.liBOW))
    
        
    # Calculate the log likihood of the content
    # setLines collection of unique preprocessed words in the email
    def LLR(self,setWords):
        probCHam =0.0
        probCSpam=0.0
        
                 
        for i, tProbs in self.dfProb.iterrows():
            if tProbs['word'] in setWords:
                    probCHam+=math.log(tProbs['pPresHam']+0.5)
                    probCSpam+=math.log(tProbs['pPresSpam']+0.5)
            else:
                probCHam+=math.log(tProbs['pAbsHam']+0.5)
                probCSpam+=math.log(tProbs['pAbsSpam']+0.5)                
            #if DEBUG:
                #print "Probs Ham {},Spam {}".format(probCHam,probCSpam)
        return (probCHam-probCSpam)      
    
######## Main ###################################

#Get all the file names for the message corpus

# list of indecies of training emails to use while creating algorithm
#indx = [0,1,2,3,4,14,26,67,68,328,403,426,515,851,970]
#indx=[0,1,2,3,4,14,26,67,68,328,403]
indx=[]
directoryList = {'dir':['easy_ham','easy_ham_2','hard_ham','spam','spam_2'],'isSpam':[False,False,False,True,True]}
#directoryList = {'dir':['easy_ham','spam'],'isSpam':[False,True]}

#create Naive Bayes Instance
NB=NaiveBayesFilter()
#load the emails and preprocess them to produce a list of unque word sets per email.
NB.importParseCorpus(directoryList,indx)  # get jsut the subset for developing with. 
#get the list of training vs testing data sets. 
trainIdx,testIdx = NB.splitCorpus(0.66)
NB.createBOW(trainIdx)
NB.trainFilter(trainIdx)
# run test
#get first test email
print "Test Email"
print NB._dfPreprocessedEmails.iloc[testIdx]['isSpam']
for i in testIdx:
    print "Is spam {}; LLR = {}".format(NB._dfPreprocessedEmails.iloc[i]['isSpam'],NB.LLR(NB._dfPreprocessedEmails.iloc[i]['words']))
