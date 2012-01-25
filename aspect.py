
class AspectError(Exception):
    pass

class MethodDescriptor(object):
    def __init__(self, method, pointcuts):
        self.method = method
        self.pointcuts = pointcuts

    def __get__(self, obj, cls):
        return MethodWrapper(self, obj, cls, self.method,
                             self.pointcuts)
                
class MethodWrapper(object):
    def __init__(self, parent, object, cls, method, pointcuts):
        self.method = method
        self.object = object
        self.pointcuts = pointcuts
        self.cls = cls
        
    def getClass(self):
        return self.cls
    
    def __call__(self, *args, **kw):
        event = Event(Event.before, self.object,
                      self.method, args, kw)
        for pc in self.pointcuts:
            pc.notifyBefore(event)

        event = Event(Event.around, self.object,
                      self.method, args, kw)
        pcs = filter(lambda x: x.isAdvisable(event),
                     self.pointcuts)
        event.setPcs(pcs)
        ret = event.callNextFunction(*args, **kw)

        event = Event(Event.after, self.object,
                      self.method, args, kw)
        for pc in self.pointcuts:
            pc.notifyAfter(event)
        return ret
        
    
class Advisable(type):
    pointcuts = []
    def __init__(cls, name, bases, attrs):
        super(Advisable, cls).__init__(name, bases, attrs)
        for key, value in attrs.items():
            if callable(value):
                setattr(cls, key,
                        MethodDescriptor(value, Advisable.pointcuts))

class Event(object):
    before = 1
    after = 2
    around = 3
    
    def __init__(self, when, object, method, args, kw):
        self.when = when
        self.object = object
        self.method = method
        self.args = args
        self.kw = kw
        self.pcs = None
        self.argmap = None

    def getTime(self):
        return self.when

    def setTime(self, when):
        self.when = when
        
    def getMethod(self):
        """ return *unwrapped* method """
        if hasattr(self.method, "method"):
            return self.method.method
        else:
            return self.method

    def getMethodName(self):
        return self.getMethod().__name__
    
    def getObjectClass(self):
        return self.object.__class__

    def getObject(self):
        return self.object
    
    def getArg(self, argname):
        from inspect import getargspec
        if not self.argmap:
            argnames = getargspec(self.getMethod())[0]
            # XXX: will 1st arg always be instance?
            self.argmap = dict(zip(argnames[1:], self.args))
        return self.argmap[argname]

    def getArgs(self):
        return self.args
    
    def setPcs(self, pcs):
        self.pcs = pcs
        
    def callNextFunction(self, *args, **kw):
        if self.pcs is None:
            raise AspectError("Attempted to callNextFunction" +
                              "from before or after advice")
        elif len(self.pcs) == 0:
            return apply(self.method, (self.object,)+args,
                         kw)
        else:
            self.args = args
            self.kw = kw
            pc = self.pcs[0]
            self.pcs = self.pcs[1:]
            return pc.executeAdvice(self)
            

class AdviceTimer:
    def __init__(self, when, pc):
        self.when = when
        self.pc = pc

    def notifyBefore(self, event):
        self.pc.notifyBefore(event)
        if (self.pc.isAdvisable(event) and
            self.getTime() == Event.before):
            self.pc.executeAdvice(event)

    def notifyAfter(self, event):
        self.pc.notifyAfter(event)
        if (self.pc.isAdvisable(event) and
            self.getTime() == Event.after):
            self.pc.executeAdvice(event)

    def getTime(self):
        return self.when
    
    def isAdvisable(self, event):
        return (event.getTime() == self.getTime() and
                self.pc.isAdvisable(event))

    def __getattr__(self, name):
        return getattr(self.pc, name)
        
        

class Pointcut(object):
    def __init__(self):
        self.advice = None
        self.when = None
        self.parent = None
        
    def notifyBefore(self, event):
        pass

    def notifyAfter(self, event):
        pass

    def isAdvisable(self, event):
        raise 'must override'

    def setAdvice(self, advice):
        if self.advice:
            raise AspectError("attempt to add advice to"+
                              " PC which already has some")
        else:
            self.advice = advice

    def getAdvice(self):
        return self.advice

    def executeAdvice(self, event):
        return self.advice(event)
        
    def __or__(self, pc):
        return OrPointcut(self, pc)

    def __and__(self, pc):
        return AndPointcut(self, pc)

    def __invert__(self):
        return NotPointcut(self)

class OrPointcut(Pointcut):
    def __init__(self, pc1, pc2):
        super(OrPointcut, self).__init__()
        self.pc1 = pc1
        self.pc2 = pc2

    def isAdvisable(self, event):
        return (self.pc1.isAdvisable(event) or
                self.pc2.isAdvisable(event))

    def notifyBefore(self, event):
        self.pc1.notifyBefore(event)
        self.pc2.notifyBefore(event)

    def notifyAfter(self, event):
        self.pc1.notifyAfter(event)
        self.pc2.notifyAfter(event)

    def copy(self):
        return OrPointcut(self.pc1.copy(), self.pc2.copy())
    
class AndPointcut(Pointcut):
    def __init__(self, pc1, pc2):
        super(AndPointcut, self).__init__()
        self.pc1 = pc1
        self.pc2 = pc2

    def isAdvisable(self, event):
        return (self.pc1.isAdvisable(event) and
                self.pc2.isAdvisable(event))

    def notifyBefore(self, event):
        self.pc1.notifyBefore(event)
        self.pc2.notifyBefore(event)

    def notifyAfter(self, event):
        self.pc1.notifyAfter(event)
        self.pc2.notifyAfter(event)

    def copy(self):
        return AndPointcut(self.pc1.copy(), self.pc2.copy())

class NotPointcut(Pointcut):
    def __init__(self, pc):
        super(NotPointcut, self).__init__()
        self.pc = pc
        
    def isAdvisable(self, event):
        return not self.pc.isAdvisable(event)

    def notifyBefore(self, event):
        self.pc.notifyBefore(event)

    def notifyAfter(self, event):
        self.pc.notifyAfter(event)

    def copy(self):
        return NotPointcut(self.pc.copy())
    
class Call(Pointcut):
    def __init__(self, wrapper):
        super(Call, self).__init__()
        self.wrapper = wrapper

    def getMethodName(self):
        return self.wrapper.method.__name__
    
    def isAdvisable(self, event):
        return (self.getMethodName() == event.getMethodName() and
                isinstance(event.getObject(), self.wrapper.getClass()))

    def copy(self):
        return Call(self.wrapper)
    
class CFlow(Pointcut):
    def __init__(self, pc, watermark=0):
        super(CFlow, self).__init__()
        self.pc = pc
        self.level = 0
        self.watermark = watermark
        
    def notifyBefore(self, event):
        self.pc.notifyBefore(event)
        if self.pc.isAdvisable(event):
            self.level += 1

    def notifyAfter(self, event):
        self.pc.notifyAfter(event)
        if self.pc.isAdvisable(event):
            self.level -= 1
            
    def isAdvisable(self, event):
        return self.level > self.watermark

    def copy(self):
        return CFlow(self.pc.copy(), self.watermark)
    

def CFlowBelow(pc):
    return CFlow(pc, 1)

def around(pcd, advice):
    pcd.setAdvice(advice)
    Advisable.pointcuts.append(AdviceTimer(Event.around, pcd))

def before(pcd, advice):
    pcd.setAdvice(advice)
    Advisable.pointcuts.append(AdviceTimer(Event.before, pcd))

def after(pcd, advice):
    pcd.setAdvice(advice)
    Advisable.pointcuts.append(AdviceTimer(Event.after, pcd))
#######################################
#

