AspectP: A Simple Aspect Oriented Programming System for Python
===============================================================

AspectP was written as part of my master's thesis in 2003.  It follows
the spirit of AspectJ and consists of a metaclass `Advisable` together
with a simple system for specifying pointcuts.  The pointcut system is
an example of the composite pattern, and the effect is to create a DSL
in python for specifying when to run a piece of advice.

Included is an example of speeding up a Fibonacci function.

This code is licensed under the GPLv3.
