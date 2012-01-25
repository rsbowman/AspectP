from unittest import TestCase

from aspect import Advisable, Event, Pointcut, OrPointcut, AndPointcut, \
     NotPointcut, Call, CFlow, CFlowBelow, around, before, after

class AdvisableTests(TestCase):
    def testUnadvisedCall(self):
        class Foo(object):
            __metaclass__ = Advisable
            def a(self, i):
                return i + 1
            def b(self, *args):
                return args
            def c(self, i, **kw):
                return kw[i]
        f = Foo()
        self.assertEqual(f.a(4), 5)
        self.assertEqual(f.b('a', 'b'), ('a', 'b'))
        self.assertEqual(f.c('c', c=4, d=5), 4)

            
## from aspect import Pointcut, OrPointcut, AndPointcut, NotPointcut, \
##      Call, CFlow, CFlowBelow, before, after

class EventTests(TestCase):
    def testMethods(self):
        class Foo:
            def bar(self, i):
                pass
        args, kw = (1,), {}
        f = Foo()
        e = Event(Event.around, f, Foo.bar, args, kw)
        self.assertEqual(e.getMethod(), Foo.bar)
        self.assertEqual(e.getObjectClass(), Foo)
        self.assertEqual(e.getArgs(), args)
        self.assertEqual(e.getObject(), f)


##         ex = TypeError('not enough poo')
##         e = Event(f, Foo.bar, args, kw,
##                   exception=ex)
##         self.assertEqual(e.getException(), ex)

    def testGetArg(self):
        class Foo:
            __metaclass__ = Advisable
            def bar(self, i, j):
                pass
        i, j = 11, 72
        e = Event(Event.around, Foo(), Foo.bar, (i, j), {})
        self.assertEqual(e.getArg('i'), i)
        self.assertEqual(e.getArg('j'), j)
        
class PointcutTests(TestCase):
    class Advice:
        event = None
        def __call__(self, event):
            self.event = event

    class P(Pointcut):
        def __init__(self, advisep=False):
            super(PointcutTests.P, self).__init__()
            self.advisep = advisep
        def isAdvisable(self, event):
            return self.advisep
        def notifyBefore(self, event):
            self.before = 1
        def notifyAfter(self, event):
            self.after = 1
            
    def testComposites(self):
        e = 'hey'
        pc = self.P() | self.P()
        self.assertEqual(pc.__class__, OrPointcut)
        self.assertEqual(pc.isAdvisable(e), False)
        pc = self.P() | self.P(True)
        self.assertEqual(pc.isAdvisable(e), True)

        pc = self.P() & self.P()
        self.assertEqual(pc.__class__, AndPointcut)
        self.assertEqual(pc.isAdvisable(e), False)
        pc = self.P(True) & self.P()
        self.assertEqual(pc.isAdvisable(e), False)
        pc = self.P(True) & self.P(True)
        self.assertEqual(pc.isAdvisable(e), True)

    def testNegation(self):
        pc = ~self.P(True)
        e = 'hey'
        self.assertEqual(pc.__class__, NotPointcut)
        self.assertEqual(pc.isAdvisable(e), False)

        pc = ~self.P()
        self.assertEqual(pc.isAdvisable(e), True)
        
class CallCFlowTests(TestCase):
    class Boo:
        __metaclass__ = Advisable
        def bar(self):
            pass
    class Foo:
        __metaclass__ = Advisable
        def bar(self):
            self.baz()
        def baz(self):
            pass

    def testCall(self):
        Foo = self.Foo
        Boo = self.Boo
        pc = Call(Foo.bar)
        pc.setAdvice(lambda x: x)
        e = Event(Event.around, Foo(), Foo.baz, (), {})
        self.assertEqual(pc.isAdvisable(e), False)
        e = Event(Event.around, Foo(), Foo.bar, (), {})
        self.assertEqual(pc.isAdvisable(e), True)
        e = Event(Event.around, Boo(), Boo.bar, (), {})
        self.assertEqual(pc.isAdvisable(e), False)

    def testCFlow(self):
        Foo, Boo = self.Foo, self.Boo
        p = CFlow(Call(Foo.bar))
        p.setAdvice(lambda x: x)
        e_uninteresting = Event(Event.around, Boo(), Boo.bar, (), {})
        e = Event(Event.around, Foo(), Foo.bar, (), {})
        self.assertEqual(p.isAdvisable(e), False)
        
        p.notifyBefore(e_uninteresting)
        self.assertEqual(p.isAdvisable(e), False)
        
        p.notifyBefore(e)
        self.assertEqual(p.isAdvisable(e), True)
        
        p.notifyAfter(e)
        self.assertEqual(p.isAdvisable(e), False)


        
class FunctionalTests(TestCase):
    def setUp(self):
        class Foo:
            __metaclass__ = Advisable
            def recursive(self, i):
                if i <= 0:
                    return 1
                else:
                    return i*self.recursive(i - 1)
            def bar(self):
                self.baz()
            def baz(self):
                self.zab()
            def zab(self):
                pass
            
        class Advice:
            def __init__(self):
                self.events = []
            def notify(self, event):
                self.events.append(event)
                r = apply(event.callNextFunction, event.getArgs())
                return r
            def append1(self, event):
                self.events.append(1)
            def append2(self, event):
                self.events.append(2)
        self.Foo = Foo
        self.Advice = Advice
        
    def tearDown(self):
        del self.Foo
        del self.Advice
        
    def testRecursive(self):
        Foo = self.Foo
        f = Foo()
        pc = Call(Foo.recursive) & ~CFlowBelow(Call(Foo.recursive))
        advice = self.Advice()
        around(pc, advice.notify)
        self.assertEqual(f.recursive(5), 120)
        self.assertEqual(len(advice.events), 1)

    def testOrder(self):
        Foo = self.Foo
        a = self.Advice()
        pc = Call(Foo.baz)
        before(pc, a.append1)
        before(pc.copy(), a.append2)
        
        f = Foo()
        f.baz()

        self.assertEqual(a.events, [1, 2])

    def testCFlow(self):
        Foo = self.Foo
        advice = self.Advice()
        f = Foo()
        bazInBoo = Call(Foo.baz) & CFlow(Call(Foo.bar))
        around(bazInBoo, advice.notify)
        f.baz()
        self.assertEqual(len(advice.events), 0)
        f.bar()
        self.assertEqual(len(advice.events), 1)

    def testCflowNesting(self):
        Foo = self.Foo
        advice = self.Advice()
        f = Foo()
        pc = CFlow(Call(Foo.bar))
        around(pc, advice.notify)
        f.bar()
        self.assertEqual(len(advice.events), 3)
        
    def testCflow(self):
        class Foo:
            __metaclass__ = Advisable
            def foo(self):
                self.bar()
            def bar(self):
                pass
        a = self.Advice()
        f = Foo()
        pc = CFlow(Call(Foo.foo))
        around(pc, a.notify)
        f.foo()
        self.assertEqual(len(a.events), 2)

    def testTwoClasses(self):
        class Foo:
            __metaclass__ = Advisable
            def foo(self, b):
                b.bar()
        class Bar:
            __metaclass__ = Advisable
            def bar(self):
                pass
        pc = Call(Bar.bar) & CFlow(Call(Foo.foo))
        a = self.Advice()
        around(pc, a.notify)
        f = Foo()
        b = Bar()
        f.foo(b)
        self.assertEqual(len(a.events), 1)
        self.assertEqual(a.events[0].getMethod().__name__, 'bar')
        
    def testOrPc(self):
        class Foo:
            __metaclass__ = Advisable
            def foo(self):
                self.bar()
            def bar(self):
                self.baz()
            def baz(self):
                pass

        pc = CFlow(Call(Foo.bar) & CFlow(Call(Foo.foo)))
        f = Foo()
        a = self.Advice()
        around(pc, a.notify)
        f.bar()
        f.baz()
        self.assertEqual(len(a.events), 0)
        f.foo()
        self.assertEqual(len(a.events), 2)
        self.assertEqual(a.events[0].getMethod().__name__, 'bar')
        self.assertEqual(a.events[1].getMethod().__name__, 'baz')

    def testSubclass(self):
        class Foo:
            __metaclass__ = Advisable
            def foo(self):
                pass            
        class Bar(Foo):
            def foo(self):
                pass
        b = Bar()
        a = self.Advice()
        pc = Call(Foo.foo)
        around(pc, a.notify)
        b.foo()
        self.assertEqual(len(a.events), 1)
        
def suite(allTests=(AdvisableTests, EventTests,
                    PointcutTests, CallCFlowTests,
                    FunctionalTests)):

    from unittest import makeSuite, TestSuite

    suites = []
    for test in allTests:
        if not isinstance(test,TestSuite):
            test = makeSuite(test, 'test')
        suites.append(test)
        
    return TestSuite(suites)

if __name__ == '__main__':
        from unittest import main
        main(defaultTest='suite')
