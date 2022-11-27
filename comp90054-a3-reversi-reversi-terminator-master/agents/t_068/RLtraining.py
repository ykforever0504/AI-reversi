from template import Agent
import random, time
from Reversi.reversi_model import ReversiGameRule
from Reversi.reversi_utils import Cell, GRID_SIZE
import json
import copy

# Define the constant
TIME_LIMIT = 0.97  # less than theoretical 1 second
NUM_OF_PLAYER = 2

ALPHA = 0.1
EPSILON = 0.1
GAMMA = 0.9

# significant squares
CORNER = [(0, 0), (0, 7), (7, 0), (7, 7)]  # best
X_SQUARE = [(1, 1), (1, 6), (6, 1), (6, 6)]
C_SQUARE = [(0, 1), (1, 0), (0, 6), (1, 7), (6, 0), (7, 1), (7, 6), (6, 7)]
EDGE = [(2, 0), (3, 0), (4, 0), (5, 0),
        (2, 7), (3, 7), (4, 7), (5, 7),
        (0, 2), (0, 3), (0, 4), (0, 5),
        (7, 2), (7, 3), (7, 4), (7, 5)]
INNER_SQAURE = [(2, 2), (2, 3), (2, 4), (2, 5),
                (3, 2), (4, 2), (3, 5), (4, 5),
                (5, 2), (5, 3), (5, 4), (5, 5)]
MIDDLE_SQAURE = [(2, 1), (3, 1), (4, 1), (5, 1),
                 (1, 2), (1, 3), (1, 4), (1, 5),
                 (6, 2), (6, 3), (6, 4), (6, 5),
                 (2, 6), (3, 6), (4, 6), (5, 6)]


class myAgent(Agent):
    def __init__(self, _id):
        super().__init__(_id)

        self.gameRule = ReversiGameRule(NUM_OF_PLAYER)
        self.rival_id = 1 - _id
        self.selfColor = self.gameRule.agent_colors[_id]
        self.weight = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        with open("agents/t_068/weight.json", 'r', encoding='utf-8') as weight:
            self.weight = json.load(weight)['weight']

    def GetSelfActions(self, state):
        return self.gameRule.getLegalActions(state, self.id)

    def GetRivalActions(self, state):
        return self.gameRule.getLegalActions(state, self.rival_id)

    def ExcuteSelfAction(self, state, action):
        nextState = self.gameRule.generateSuccessor(state, action, self.id)
        return nextState

    def ExcuteRivalAction(self, state, action):
        nextState = self.gameRule.generateSuccessor(state, action, self.rival_id)
        return nextState

    def GameEnd(self, state):
        return (self.GetSelfActions(state) == ["Pass"] and self.GetRivalActions(state) == ["Pass"])

    def CalReward(self, state, features, end=False):
        corner_reward = 0
        if end:
            corner_diff = features[3] * len(CORNER) - (len(CORNER) - features[3] * len(CORNER))
            corner_reward = corner_diff * 5

        score_reward = self.gameRule.calScore(state, self.id) - self.gameRule.calScore(state, self.rival_id)

        return corner_reward + score_reward

    # return the intersection of two lists
    def list_intersection(self, list1, list2):
        return list(set(list1).intersection(set(list2)))

    # return the difference between two lists
    def list_difference(self, list1, list2):
        return list(set(list1).difference(set(list2)))

    def CalFeature(self, state, action):
        features = []
        nextState = self.ExcuteSelfAction(state, action)
        oppoActions = self.GetRivalActions(nextState)

        # Feature1 - Self score
        f1 = self.gameRule.calScore(nextState, self.id)
        # Feature2 - Opponent score
        f2 = self.gameRule.calScore(nextState, self.rival_id)
        # Feature6 - Opponent possible moves towards corners
        f6 = len(set(oppoActions).intersection(set(CORNER)))
        # Feature7 - Opponent mobility count
        f7 = len(set(oppoActions))
        # Feature8 - Opponent possible moves towards edges
        f8 = len(set(oppoActions).intersection(set(EDGE)))
        # Feature9 - Opponent possible moves towards X squares
        f9 = len(set(oppoActions).intersection(set(X_SQUARE)))
        # Feature10 - Opponent possible moves towards C squares
        f10 = len(set(oppoActions).intersection(set(C_SQUARE)))

        visited = set()

        def BrfsFindEdge(pos):
            temp = 0
            if pos[0] < 0 or pos[0] > GRID_SIZE - 1 or pos[1] < 0 or pos[1] > GRID_SIZE - 1:
                return 0
            if pos in visited:
                return 0
            if nextState.board[pos[0]][pos[1]] == self.selfColor:
                visited.add(pos)
                temp += 1
                temp += BrfsFindEdge((pos[0] + 1, pos[1]))
                temp += BrfsFindEdge((pos[0] - 1, pos[1]))
                temp += BrfsFindEdge((pos[0], pos[1] + 1))
                temp += BrfsFindEdge((pos[0], pos[1] - 1))
            return temp

        # Feature3 - Self corner count, initialised first
        # Feature4 - Self subcorner count, initialised first
        # Feature5 - Self permanent edges count, initialised first
        f3, f4, f5 = 0, 0, 0
        for i in range(len(CORNER)):
            if nextState.board[CORNER[i][0]][CORNER[i][1]] == self.selfColor:
                f3 += 1
                f5 += BrfsFindEdge(CORNER[i])
            if nextState.board[CORNER[i][0]][CORNER[i][1]] == Cell.EMPTY \
                    and nextState.board[X_SQUARE[i][0]][X_SQUARE[i][1]] == self.selfColor:
                f4 += 1

        # Normalise the features count
        features.append(f1 / (GRID_SIZE * GRID_SIZE))
        features.append(f2 / (GRID_SIZE * GRID_SIZE))
        features.append(f3 / len(CORNER))
        features.append(f4 / len(X_SQUARE))
        features.append(f5 / (len(CORNER) * GRID_SIZE - len(CORNER)))
        features.append(f6 / len(CORNER))
        features.append(f7 / (GRID_SIZE * GRID_SIZE))
        features.append(f8 / len(EDGE))
        features.append(f9 / len(X_SQUARE))
        features.append(f10 / len(C_SQUARE))

        return features

    def CalQ(self, state, action):
        features = self.CalFeature(state, action)
        if len(self.weight) != len(features):
            return -float('inf')
        else:
            q_value = 0
            for i in range(len(features)):
                q_value += self.weight[i] * features[i]
            return q_value

    def CutTree(self, actions, gameState):
        # Keep the corners only if there is any
        corners = self.list_intersection(actions, CORNER)
        if len(corners) == 1:
            return corners[0]
        if len(corners) > 0:
            actions = corners

        # Check X-squares which is neighbor of selftaken corners
        # since if any corner is put on, neighboring x-squares would be good
        x_squares = self.list_intersection(actions, X_SQUARE)
        temp_actions = copy.deepcopy(actions)
        x_neighbors = []

        if len(x_squares) > 0:

            for square in CORNER:
                x_co, y_co = square
                if gameState.board[x_co][y_co] == self.selfColor:
                    taken_corner_index = CORNER.index((x_co, y_co))
                    x_neighbors.append(X_SQUARE[taken_corner_index])

            # Remove non-neighbor X-squares of taken corners
            # and revert actions if none of action is left
            for x in x_squares:
                if x not in x_neighbors:
                    actions.remove(x)

            if len(actions) == 0:
                actions = temp_actions

        # Check C-squares which is neighbor of self-taken corners
        # since if any corner is put on, neighboring c-squares would be good
        c_squares = self.list_intersection(actions, C_SQUARE)
        temp_actions = copy.deepcopy(actions)
        c_neighbors = []

        if len(c_squares) > 0:

            for square in CORNER:
                x_co, y_co = square
                if gameState.board[x_co][y_co] == self.selfColor:
                    taken_corner_index = CORNER.index((x_co, y_co))
                    c_neighbors.append(C_SQUARE[2 * taken_corner_index])
                    c_neighbors.append(C_SQUARE[2 * taken_corner_index + 1])

            # Remove non-neighbor C-squares of taken corners
            # and revert actions if none of action is left
            for c in c_squares:
                if c not in c_neighbors:
                    actions.remove(c)

            if len(actions) == 0:
                actions = temp_actions

        return actions

    def SelectAction(self, actions, gameState):
        # init:change to the current state
        self.gameRule.agent_colors = gameState.agent_colors

        # Cut the tree options
        actions = self.CutTree(actions, gameState)

        # If the tree is cut to only one corner
        if actions in CORNER:
            return actions

        solution = random.choice(actions)

        best_q = -float('inf')
        startTime = time.time()

        # E-greedy, update best Q value
        if random.uniform(0, 1) < 1 - EPSILON:
            for action in actions:
                if time.time() - startTime > TIME_LIMIT:
                    print("time out")
                    break
                q_value = self.CalQ(gameState, action)
                if q_value > best_q:
                    best_q = q_value
                    solution = action
        else:
            q_value = self.CalQ(gameState, solution)
            best_q = q_value

        # Simulate opponent's action
        nextState = self.ExcuteSelfAction(gameState, solution)
        oppoActions = self.GetRivalActions(nextState)
        oppoBestScore = 0
        oppoBestState = nextState
        for oppoAction in oppoActions:
            oppoNextState = self.ExcuteRivalAction(nextState, oppoAction)
            oppoNextScore = self.gameRule.calScore(nextState, self.rival_id)
            if oppoNextScore > oppoBestScore:
                oppoBestScore = oppoNextScore
                oppoBestState = oppoNextState
        nextState = oppoBestState

        # update best Q value in next state
        nextActions = self.GetSelfActions(nextState)
        best_next_q = -float('inf')
        for nextAction in nextActions:
            if time.time() - startTime > TIME_LIMIT:
                print("time out")
                break
            q_value = self.CalQ(nextState, nextAction)
            best_next_q = max(best_next_q, q_value)

        features = self.CalFeature(gameState, solution)

        if self.GameEnd(nextState):
            reward = self.CalReward(nextState, features, end=True)
        else:
            reward = self.CalReward(nextState, features)

        delta = reward + GAMMA * best_next_q - best_q
        for i in range(len(features)):
            self.weight[i] += ALPHA * delta * features[i]

        print("UPDATE")
        print("reward:", reward, "    ", "delta:", delta)
        print("best_next_q:", best_next_q, "    ", "best_q:", best_q)
        print(self.weight)
        print("-" * 20)
        with open('agents/t_068/weight.json', 'w', encoding='utf-8') as write:
            json.dump({"weight": self.weight}, write, indent=4, ensure_ascii=False)

        return solution