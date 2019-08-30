import xml.etree.ElementTree as ET
from os import path

class DFA:
    def __init__(self, filename=None, numOfStates=0):
        self.states = [None] * numOfStates
        self.initialIndex = 0 

        if filename is not None:
            # automaton section in the .jff
            root = ET.parse(filename).getroot().getchildren()[1]
            for child in root:
                if child.tag == "state":
                    state = State(int(child.get("id")), child.find("final") is not None)
                    if child.find("initial") is not None:
                        self.initialIndex = state.index

                    # Expands list if index is beyond it
                    if state.index >= len(self.states):
                        self.states.extend([None] * (state.index - (len(self.states) - 1)))
                    self.states[state.index] = state
                else:
                    fromIndex = int(child.find("from").text)
                    transition = child.find("read").text
                    toIndex = int(child.find("to").text)
                    self.addTransition(fromIndex, toIndex, transition)

    def addState(self, stateIndex, final):
        self.states[stateIndex] = State(stateIndex, final)

    def addTransition(self, fromIndex, toIndex, char):
        self.states[fromIndex].transitions[char] = toIndex

    # returns the stateIndex of the state obtained from performing the transition
    # from the passed stateIndex, or None if the transition doesn't exist
    def performTransition(self, stateIndex, transition):
        return self.states[stateIndex].transitions.get(transition)

    def isFinal(self, stateIndex):
        return self.states[stateIndex].final

    def __repr__(self):
        return str(self.__dict__)

class State:
    def __init__(self, index, final):
        self.index = index
        self.final = final
        self.transitions = {}

    def __repr__(self):
        return str(self.__dict__)

def getFilename(prompt):
    while True:
        filename = input(prompt)
        if path.exists(filename):
            return filename
        else:
            print("Invalid filename, try again")
        
# Returns DFA containing the raw intersection between graph1 and graph2
def solve(graph1, graph2):
    intersection = DFA(numOfStates=len(graph1.states) * len(graph2.states))
    intersection.initialIndex = graph1.initialIndex * len(graph2.states) + graph2.initialIndex
    intersection.addState(intersection.initialIndex, graph1.isFinal(graph1.initialIndex) \
        and graph2.isFinal(graph2.initialIndex))    

    def solveInner(state1Index, state2Index):
        intersectionStateIndex = state1Index * len(graph2.states) + state2Index

        for transition in graph1.states[state1Index].transitions:
            newState1Index = graph1.performTransition(state1Index, transition)
            newState2Index = graph2.performTransition(state2Index, transition)

            # Transition exists from state2
            if newState2Index is not None:
                newIntersectionStateIndex = newState1Index * len(graph2.states) + newState2Index

                # Adds the transition from the previous state in the intersection to the new state
                intersection.addTransition(intersectionStateIndex, newIntersectionStateIndex, transition)

                # State in the intersection has not been visited yet
                if intersection.states[newIntersectionStateIndex] is None:
                    # Creates new state in the intersection
                    newState1Final = graph1.isFinal(newState1Index)
                    newState2Final = graph2.isFinal(newState2Index)
                    intersection.addState(newIntersectionStateIndex, newState1Final and newState2Final)
                    solveInner(newState1Index, newState2Index)

    solveInner(graph1.initialIndex, graph2.initialIndex)
    return intersection

# Minimises all the state indices to be a contiguous series starting from 0
def reformat(dfa):
    remappings = {}
    newStates = []
    newStateIndex = 0

    # Updates all state indices
    for state in dfa.states:
        if state is not None:
            newStates.append(state)
            remappings[state.index] = newStateIndex
            if dfa.initialIndex == state.index:
                dfa.initialIndex = newStateIndex
            state.index = newStateIndex
            newStateIndex += 1

    # Updates all the stateIndex's in all transitions
    for state in newStates:
        for transition, oldState in state.transitions.items():
            state.transitions[transition] = remappings[oldState]

    dfa.states = newStates

# Removes all states that do not lead to final states
def minimise(dfa):
    path = []
    valid = [None] * len(dfa.states)

    def minimiseInner(stateIndex):
        nonlocal valid
        valid[stateIndex] = dfa.isFinal(stateIndex)
        path.append(stateIndex)
        
        for transition in dfa.states[stateIndex].transitions:
            newStateIndex = dfa.performTransition(stateIndex, transition)
            result = False
            
            # Loop found
            if newStateIndex in path:
                if valid[newStateIndex] is False:
                    result = newStateIndex
                else:
                    result = valid[newStateIndex]
            else:
                if valid[newStateIndex] is None:
                    minimiseInner(newStateIndex)
                result = valid[newStateIndex]

            if valid[stateIndex] is not True:
                if type(result) is int:
                    # No previous result or result is further backwards in the path
                    if type(valid[stateIndex]) is not int or \
                        path.index(result) < path.index(valid[stateIndex]):
                        valid[stateIndex] = result
                        # Updates all states dependant on this state
                        valid = [result if x is stateIndex else x for x in valid]
                elif result is True:
                    valid[stateIndex] = True
                    # Updates all states dependant on this state
                    valid = [True if x is stateIndex else x for x in valid]
                        
        if valid[stateIndex] is stateIndex:
            valid[stateIndex] = False
            valid = [False if x is stateIndex else x for x in valid]

        path.pop()

    minimiseInner(dfa.initialIndex)

    # Removes invalid states
    dfa.states = [state for state in dfa.states if valid[state.index] is True]

    # Removes transitions to invalid states
    for state in dfa.states:
        state.transitions = {char : stateIndex for char, stateIndex in state.transitions.items() \
            if valid[stateIndex] is True}
                
def writeToFile(dfa, filename):
    output = '<?xml version="1.0" encoding="UTF-8" standalone="no"?><structure><type>fa</type><automaton>'
    xOffset = 0
    yOffset = 0
    for state in dfa.states:
        output += '<state id="%d" name="q%d"><x>%f</x><y>%f</y>%s%s</state>' \
        % (state.index, state.index, xOffset, yOffset, \
        "<initial/>" if state.index == dfa.initialIndex else "", "<final/>" if state.final else "")
        for transition in state.transitions:
            output += '<transition><from>%d</from><to>%d</to><read>%s</read></transition>' \
            % (state.index, state.transitions[transition], transition)

        xOffset += 100
        if xOffset == 600:
            yOffset += 100
            xOffset = 0

    output += '</automaton></structure>'
    file1 = open(filename, "w")
    file1.write(output)
    file1.close()

graph1Filename = getFilename("Graph 1 filename: ")
graph2Filename = getFilename("Graph 2 filename: ")
outputFilename = input("Output graph filename: ")

graph1 = DFA(filename=graph1Filename)
graph2 = DFA(filename=graph2Filename)

intersection = solve(graph1, graph2)
reformat(intersection)
minimise(intersection)
writeToFile(intersection, outputFilename)




    