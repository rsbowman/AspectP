from aspect import Advisable

class Fib:
    __metaclass__ = Advisable
    
    def fibonacci(self, n):
        print 'fib(%s)' %(n,)
        if n > 1:
            return self.fibonacci(n - 1) + self.fibonacci(n - 2)
        else:
            return 1

class CacheAdvice:
    def __init__(self):
        self.cache = {}
        self.call = 0
        
    def advice(self, event):
        n = event.getArg('n')
        if n in self.cache.keys():
            print 'found fib(%d) in cache' %(n,)
            return self.cache[n]
        else:
            print 'computing fib(%d)' %(n,)
            v = event.callNextFunction(n)
            self.cache[n] = v
            return v

    def trace(self, event):
        self.call += 1
        print 'calling %s %d' %(event.getMethod(), self.call)
        r = event.callNextFunction(event.getArg('n'))
        print 'after %s %d' %(event.getMethod(), self.call)
        self.call -= 1
        return r

    def hey(self, event):
        print 'hey'
        
if __name__ == '__main__':
    from aspect import Call, around

    def p(s):
        print s
        
    ca = CacheAdvice()
    f = Fib()
    #import pdb
    
    print 'without:'

    f.fibonacci(10)
    around(Call(Fib.fibonacci), ca.advice)
    
    #around(Call(Fib.fibonacci), ca.trace)
    
    #around(Call(Fib.fibonacci), ca.advice)

    print 'with:'
#    f.fibonacci(10)
