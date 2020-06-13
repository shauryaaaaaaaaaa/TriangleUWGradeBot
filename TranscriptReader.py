#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import PyPDF2
class PDFParser:
    def __init__(self, fileName, quarterName):
        self.fileName = fileName
        self.QUARTER_NAME = quarterName
        
        self.pdfFileObj = open(fileName, 'rb')
        self.pdfReader = PyPDF2.PdfFileReader(self.pdfFileObj)
        self.data = self.getData()
        self.first = self.getFirst()

    def getData(self):
        lastPage = self.pdfReader.getPage(self.pdfReader.numPages - 1)

        data = lastPage.extractText()

        if(self.pdfReader.numPages == 1):
            secondLastPage = self.pdfReader.getPage(self.pdfReader.numPages - 2)
            secondLastPage = secondLastPage.extractText()
            data = secondLastPage + data

        return data[-1600:][:600].split('\n')
        
    def getFirst(self):
        return self.pdfReader.getPage(0).extractText()[0:150].split('\n')
    
    def getName(self):
        for n in range(len(self.first)):
            if('UNOFFICIAL' in self.first[n]):
                self.first = self.first[n:]
                break
            
        return self.first[2]
    
    def getGPA(self):
        quarterFound = False

        for n in range(len(self.data)):
            if(self.QUARTER_NAME in self.data[n]):
                self.data = self.data[n:]
                quarterFound = True
                break

        if(not quarterFound): 
            raise ValueError('Quarter not found')

        cumIndex = -1
        qtrIndex = -1
        for n in range(len(self.data)):
            if((qtrIndex == -1) and ('0 GPA:  ' in self.data[n])):
                qtrIndex = n
            if((cumIndex == -1) and ('CUM GPA:  ' in self.data[n])):
                cumIndex = n

        if(qtrIndex == -1 or cumIndex == -1):
            raise ValueError('GPA not found')

        cumGPA = self.data[cumIndex][-4:]
        qtrGPA = self.data[qtrIndex][-4:]
        
        return qtrGPA, cumGPA
    
    def closeFile(self):
        self.pdfFileObj.close()
        return

