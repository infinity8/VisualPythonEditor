'''
Created on 29 Jan 2014

@author: Philip
'''

import Queue
import copy

# This Data class is used to wrap all data in the program to allow for simple automatic iteration
dataClass = \
"""class Data:
    def __init__(self, values, data=None, iteration="Single", orientation="Row", index=0):
        if not hasattr(values, '__iter__'):
            values = [values]
        for i in range(len(values)):
            if not hasattr(values[i], '__iter__'):
                values[i] = [values[i]]
        self.values = values
        self.iteration = iteration
        self.orientation = orientation
        self.index = index
        if data != None:
            self.iteration = data.iteration
            self.orientation = data.orientation
            self.index = data.index

    def wrapIndex(self, index):
        if self.iteration == "Single":
            if index >= len(self):
                index = len(self)-1
        elif self.iteration == "Wrapped":
            index = index % (len(self)-1)
        return index    

    def __getitem__(self, key):
        key = self.wrapIndex(key)
        if self.orientation == "Row":
            return self.values[key][self.index]
        elif self.orientation == "Column":
            return self.values[self.index][key]

    def __setitem__(self, key, value):
        pass

    def __len__(self):
        if self.orientation == "Row":
            return len(self.values)
        elif self.orientation == "Column":
            return len(self.values[0])
        
    def __str__(self):
        string = ""
        for i in range(len(self)):
            string += str(self[i]) + "\\n"
        return string
        
"""

class Program:
    """The root structure in the system. Has a name and a set of methods.
    """
    def __init__(self, name):
        self.methods = []
        self.name = name
        self.imports = []
    
    def addImport(self, i):
        for im in self.imports:
            if im == i:
                return
        self.imports.append(i)
    
    def addMethod(self, method):
        if not method in self.methods:
            self.methods.append(method)  
            
    def removeMethod(self, method):
        self.methods.remove(method)      

    def checkNameUsed(self, name):
        """ Checks if the given name is currently in use by a method in this program """
        for method in self.methods:
            if name == method.name:
                return True
        return False            
    def getUnusedName(self, base="Empty_Method"):
        """ Appends '0' to the base name until the name is not found in the program """
        name = base
        while self.checkNameUsed(name):
            name = name + "0"
        return name
    
    def compile(self, mainMethod):
        """ Compiles the current program into runnable python. The given mainMethod is used as the entry point call for the program. """
        code = ""
        self.imports = []
        for method in self.methods:
            imp = method.getImports()
            for i in imp:
                self.addImport(i)
        for i in self.imports:
            code += i + "\n"
        code += "\n\n"
        global dataClass
        code += dataClass
        code += "class " + self.name + ":\n"
        for method in self.methods:
            code += method.compile() + "\n\n"
        code += "program = " + self.name + "()\n"
        code += "program." + mainMethod.name + "()"
        return code

class CodeMethod:
    """ This method encompasses hard coded python. The method has normal inputs and outputs but with user defined code between them. """
    
    def __init__(self, name):
        self.name = name
        self.inputs = []
        self.outputs = []
        self.setNumInputs(1)
        self.setNumOutputs(1)
        self.code = ""
        self.editted = False
        self.deleted = False
        self.imp = []
        
    def setImports(self, imp):
        self.imp = imp
        
    def setNumInputs(self, num, baseName="Input"):
        prev = self.inputs
        self.inputs = [""] * num
        for i in range(num):
            if i < len(prev) :
                self.inputs[i] = prev[i]
            else :
                self.inputs[i] = baseName+str(i)
            
    def setNumOutputs(self, num, baseName="Output"):
        prev = self.outputs
        self.outputs = [""] * num
        for i in range(num):
            if i < len(prev) :
                self.outputs[i] = prev[i]
            else :
                self.outputs[i] = baseName+str(i)
    
    def getImports(self):
        return self.imp
    
    def compile(self):
        
        argument = "\tdef " + self.name + "(self"
        for arg in self.inputs:
            argument += ", " + arg
        argument += "):\n\t\t"
        
        output = "return ("
        first = True
        for out in self.outputs:
            if first:
                first = False
            else:
                output += ", "
            output += out
        output += ")"
        
        return argument + self.code.replace("\n", "\n\t\t") + output
                
class NodeMethod:
    """ This method encompasses a set of nodes linked together. """
    
    def __init__(self, name):
        self.name = name
        self.inputs = []
        self.nodes = []
        self.outputs = []
        self.setNumInputs(1)
        self.setNumOutputs(1)
        self.editted = False
        self.deleted = False
        
    def setNumInputs(self, num, baseName="Input"):
        prev = self.inputs
        self.inputs = [""] * num
        for i in range(num):
            if i < len(prev) :
                self.inputs[i] = prev[i]
            else :
                self.inputs[i] = baseName+str(i)
            
    def setNumOutputs(self, num, baseName="Output"):
        prev = self.outputs
        self.outputs = [""] * num
        for i in range(num):
            if i < len(prev) :
                self.outputs[i] = prev[i]
            else :
                self.outputs[i] = baseName+str(i)
        
    def addNode(self, node):
        self.nodes.append(node)
    
    def removeNode(self, node):
        self.nodes.remove(node)
    
    def getImports(self):
        imp = []
        for node in self.nodes:
            i = node.getImports()
            if i != None:
                imp.extend(i)
        return imp
    
    def updatePriority(self, code, n, p):
        """ This method propogates a priority change through the list of already processed nodes. """
        for nn in self.nodes:
            nn.releaseUpdateLock()
        
        processList = Queue.Queue()
        processList.put_nowait((n, p))
        
        while not processList.empty():
            (node, priority) = processList.get_nowait()
            
            node.priority = priority
            
            for i in range(len(code)):
                entry = code[i]
                if entry[2] == node:
                    code[i] = (priority, entry[1], entry[2])
                    break
            
            for key in node.links.keys():
                tuple = node.links[key]
                if len(tuple) == 0:
                    continue
                linked = tuple[0]

                if (not linked.updating) and (priority+1 > linked.priority):
                    processList.put_nowait((linked, priority+1))
                    linked.updating = True
    
    def compile(self):
        for node in self.nodes:
            node.reset()
        
        processList = Queue.Queue() 
        data = {}
        data["Queue"] = processList
        data["NameMap"] = {}
        data["NameMap"]["Used"] = copy.deepcopy(self.inputs)
        data["NameMap"]["Arguments"] = copy.deepcopy(self.inputs)
        data["Return"] = {}
        data["CodeMethod"] = []
        
        for node in self.nodes:
            if isinstance(node, TerminalNode):
                processList.put_nowait(node)
        
        while not processList.empty() :
            node = processList.get_nowait()
            node.process(data)
            for key in node.links.keys():
                tuple = node.links[key]
                if len(tuple) == 0:
                    continue
                linked = tuple[0]
                # Queue if needed
                if not linked.added :
                    data["Queue"].put_nowait(linked)
                    linked.added = True
                    
                if node.priority+1 > linked.priority :
                    if linked.processed:
                        self.updatePriority(data["CodeMethod"], linked, node.priority+1)
                    else:
                        linked.priority = node.priority+1
        
        data["CodeMethod"].sort(key=lambda tup: tup[0], reverse = True)
        
        method = "\tdef "+self.name+"(self"
        for input in self.inputs:
            method += ", "
            method += input
        method+="):"
        
        for line in data["CodeMethod"] :
            method += "\n\t\t"+line[1]
        
        if len(data["Return"]) > 0:
            method += "\n\t\treturn ("
            first = True
            for key in data["Return"].keys():
                if first:
                    first = False
                else:
                    method += ", "
                method += data["Return"][key]
            method += ")"
            
        return method
    
class Node:
    """ The base class that represents a node. Has a set of input links, a name and an xy position (for the GUI) """
    
    def __init__(self, name):
        self.reset()
        
        self.name = name
        self.links = {}
        self.setNumLinks(1, name)
        
        self.x = 0
        self.y = 0
    
    def reset(self):
        self.added = False
        self.processed = False
        self.priority = 0
        
    def releaseUpdateLock(self):
        self.updating = False
    
    def removeLink(self, name):
        self.links[name] = ()

    def addLink(self, name, node, nodename):
        self.links[name] = (node, nodename)
        
    def setNumLinks(self, num, baseName):
        prevLinks = self.links
        keys = prevLinks.keys()
        self.links = {}
        for i in range(num):
            if i < len(keys) :
                self.links[keys[i]] = prevLinks[keys[i]]
            else :
                self.links[baseName+str(i)] = ()
                
    def update(self):
        pass
    
    def writeCode(self, data, code):
        data["CodeMethod"].append((self.priority, code, self))
        self.processed = True
    
    def getImports(self):
        pass
    
    def getMappedName(self, node, name, nameMap):
        """ This method is used to assign an autogenerated name to the given node-name pair. This mean that the system avoids name overlap issues. """
        if node in nameMap and name in nameMap[node]:
            return nameMap[node][name]
        elif name in nameMap["Arguments"]:
            return name
        else:
            usedNames = nameMap["Used"]
                
            bn = "value"
            i = 0
            nn = bn + str(i)
            while nn in usedNames:
                i+=1
                nn = bn + str(i)
            
            usedNames.append(nn)
            
            if not node in nameMap:
                nameMap[node] = {}
            nameMap[node][name] = nn
            return nn

class StartNode(Node):
    pass
class TerminalNode(Node):
    pass
            
class ArgumentNode(StartNode):
    """ This node represents a subset of the arguments of the parent method """
    def __init__(self):
        Node.__init__(self, "Method Input")
    
    def set(self, args):
        self.links = {}
        for arg in args:
            self.links[arg] = ()
    
    def process(self, data): 
        pass
    
class ValueNode(StartNode):
    """ This node represents a hard coded value. """
    def __init__(self, name, value):
        Node.__init__(self, value)
        self.links = {}
        self.links[name] = ()
    
    def set(self, name, value):
        self.name = value
        self.links = {}
        self.links[name] = ()
    
    def process(self, data):    
        code = self.getMappedName(self, self.links.keys()[0], data["NameMap"])  + " = Data(" + self.name + ")"
        self.writeCode(data, code)
    
class OutputNode(TerminalNode):
    """ This node represents a subset of the outputs of the parent method. """
    def __init__(self):
        Node.__init__(self, "Method Output")
    
    def set(self, outs):
        self.links = {}
        for out in outs:
            self.links[out] = ()
    
    def process(self, data):
        for key in self.links.keys() :
            
            if len(self.links[key]) == 0 :
                continue
            
            (node, nodename) = self.links[key]
                
            data["Return"][key] = self.getMappedName(node, nodename, data["NameMap"])
            
        self.processed = True

class PrintNode(TerminalNode):
    """ This node represents printing the input data to stdout. """
    def __init__(self):
        Node.__init__(self, "Print")
        self.links = {}
        self.links["Print"] = ()
        
    def process(self, data):
        code = "print " + self.getMappedName(self.links["Print"][0], self.links["Print"][1], data["NameMap"])
        self.writeCode(data, code)
        
class FileWriteNode(TerminalNode):
    """ This node represents writing the input data to the input filename. """
    def __init__(self):
        Node.__init__(self, "File Write")
        
        self.links = {}
        self.links["Filename"] = ()
        self.links["Contents"] = ()
        
    def process(self, data):
        code = "file = open(" + self.getMappedName(self.links["Filename"][0], self.links["Filename"][1], data["NameMap"]) + "[0], 'w')\n\t\t"
        code += "file.write(" + self.getMappedName(self.links["Contents"][0], self.links["Contents"][1], data["NameMap"]) + ")\n\t\t"
        code += "file.close()"
        self.writeCode(data, code)

class FileReadNode(Node):
    """ This method opens the given filename and reads it in as a string block. To convert to values a node such as CSVParser needs to be used. """
    def __init__(self):
        Node.__init__(self, "File Read")
        self.outputs = []
        
        self.links = {}
        self.links["Filename"] = ()
        self.outputs.append("Contents")
    
    def process(self, data):
        code = "file = open(" + self.getMappedName(self.links["Filename"][0], self.links["Filename"][1], data["NameMap"]) + "[0], 'rb')\n\t\t"
        code += self.getMappedName(self, self.outputs[0], data["NameMap"]) + " = file.read()\n\t\t"
        code += "file.close()"
        self.writeCode(data, code)

class ArithmeticNode(Node):
    """ This node represents performing arithmetic expressions of the list of input datas. """
    def __init__(self):
        Node.__init__(self, "Add")
        self.outputs = []
        
        self.setNumInputs(2)
        self.outputs.append("Result")
        
    def setOperator(self, operation):
        self.name = operation
        
    def setNumInputs(self, num):
        prevlinks = self.links
        self.links = {}
        for i in range(num):
            key = "Input"+str(i)
            self.links[key] = ()
            if key in prevlinks:
                self.links[key] = prevlinks[key]
    
    def process(self, data):
        code = self.getMappedName(self, self.outputs[0], data["NameMap"]) + " = Data(["
        num = len(self.links)
        
        operator = "+"
        if self.name == "Subtract":
            operator = "-"
        elif self.name == "Multiply":
            operator = "*"
        elif self.name == "Divide":
            operator = "/"
            
        for i in range(num-1):
            code += "("
        for i in range(num):
            link = self.links["Input"+str(i)]
            if i > 0:
                code += " " + operator + " "
            code += self.getMappedName(link[0], link[1], data["NameMap"]) + "[i]"
            if num > 1 and i > 0 and i < num:
                code += ")"
        code += " for i in range(max("
        for i in range(num):
            link = self.links["Input"+str(i)]
            if i > 0:
                code += ", "
            code += "len(" + self.getMappedName(link[0], link[1], data["NameMap"]) + ")"
        code += "))])"
        
        self.writeCode(data, code)
 
class MethodNode(Node):
    """ This node represents a method call. """
    def __init__(self, method):
        Node.__init__(self, method.name)
        self.method = method
        self.outputs = []
        self.update()
        
    def update(self):
        self.name = self.method.name
        for key in self.method.inputs :
            if not key in self.links:
                self.links[key] = {}
            
        for key in self.method.outputs:
            if not key in self.outputs:
                self.outputs.append(key)
        
    def process(self, data):
        string = "("
        first = True
        for key in self.outputs :
            if not first :
                string += ", "
            else :
                first = False
            string += self.getMappedName(self, key, data["NameMap"])
            
        string += ") = self." + self.method.name + "("
        
        first = True
        for key in self.links.keys() :
            (node, nodename) = self.links[key]
            if not first :
                string += ", "
            else :
                first = False
            string += self.getMappedName(node, nodename, data["NameMap"])
        
        string += ")"
        
        self.writeCode(data, string)

class ConditionalSelectorNode(Node):
    """ This node represents selecting either of the input datas depending on the boolean evaluation of the given expression. """
    def __init__(self):
        Node.__init__(self, "Equals")
        self.links = {}
        self.links["TestValue1"] = ()
        self.links["TestValue2"] = ()
        self.links["SuccessValue"] = ()
        self.links["FailureValue"] = ()
        self.outputs = ["Selected"]
        
    def setOperator(self, operator):
        self.name = operator
    
    def nameToOperator(self):
        if self.name == "Equals":
            return "=="
        elif self.name == "Greater Than":
            return ">"
        elif self.name == "Equal Or Greater Than":
            return ">="
        elif self.name == "Less Than":
            return "<"
        elif self.name == "Equal Or Less Than":
            return "<="
      
    def process(self, data):
        
        code = self.getMappedName(self, self.outputs[0], data["NameMap"]) + " = Data(["
        
        code += self.getMappedName(self.links["SuccessValue"][0], self.links["SuccessValue"][1], data["NameMap"]) + "[i]"
        code += " if ("
        code += self.getMappedName(self.links["TestValue1"][0], self.links["TestValue1"][1], data["NameMap"]) + "[i]"
        code += " " + self.nameToOperator() + " "
        code += self.getMappedName(self.links["TestValue2"][0], self.links["TestValue2"][1], data["NameMap"]) + "[i]"
        code += ") else "
        code += self.getMappedName(self.links["FailureValue"][0], self.links["FailureValue"][1], data["NameMap"]) + "[i]"
        code += " for i in range(max("
        code += "len(" + self.getMappedName(self.links["TestValue1"][0], self.links["TestValue1"][1], data["NameMap"]) + "), "
        code += "len(" + self.getMappedName(self.links["TestValue2"][0], self.links["TestValue2"][1], data["NameMap"]) + ")"
        
        code += "))])"
                
        self.writeCode(data, code)
        
class CSVParserNode(Node):
    """ This node represents converting the input string into a block of csv values. """
    def __init__(self):
        Node.__init__(self, "CSV Parser")
        self.outputs = ["CSV Data"]
        
        self.links = {}
        self.links["CSV"] = ()
        
        self.delimiter = ","
        self.quotechar = '"'
        self.datatype = "float"
    
    def getImports(self):
        return ["import csv", "import StringIO"]
    
    def process(self, data):
        code = "reader = csv.reader(StringIO.StringIO(" + self.getMappedName(self.links["CSV"][0], self.links["CSV"][1], data["NameMap"]) + "), delimiter='" + self.delimiter + "', quotechar='" + self.quotechar + "')\n\t\t"
        code += self.getMappedName(self, self.outputs[0], data["NameMap"]) + " = Data([["+self.datatype+"(element) for element in row] for row in reader])"
        self.writeCode(data, code)
        
class ScatterPlotNode(TerminalNode):
    """ This node represents plotting the input datas on a scatter graph. It is added as an example of the nodes that would need to be added to make the language viable for general use. """
    def __init__(self):
        Node.__init__(self, "Scatter Plot")
        
        self.links = {}
        self.links["X"] = ()
        self.links["Y"] = ()
    
    def getImports(self):
        return ["import pylab"]
    
    def process(self, data):
        code = "pylab.scatter(" + self.getMappedName(self.links["X"][0], self.links["X"][1], data["NameMap"]) + ", " + self.getMappedName(self.links["Y"][0], self.links["Y"][1], data["NameMap"]) + ")\n\t\t"
        code += "pylab.show()"
        self.writeCode(data, code)

class DataSettingsNode(Node):
    """ This node represents changing the settings on the input data. """
    def __init__(self):
        Node.__init__(self, "Data Settings")
        self.outputs = ["Data Out"]
        
        self.links = {}
        self.links["Data In"] = ()
        
        self.orientation = "Row"
        self.iteration = "Single"
        self.index = 0
        
    def process(self, data):
        code = self.getMappedName(self, self.outputs[0], data["NameMap"]) + " = Data(" + self.getMappedName(self.links["Data In"][0], self.links["Data In"][1], data["NameMap"]) + ".values, iteration='"+self.iteration+"', orientation='"+self.orientation+"', index="+str(self.index)+")"
        self.writeCode(data, code)

class CodeNode(MethodNode):
    """ This node represents calling a code method. """
    pass







