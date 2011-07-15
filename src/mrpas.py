#!/usr/bin/env python
"""
PHP MRPAS
Copyright (c) 2010 Dominik Marczuk
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * The name of Dominik Marczuk may not be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY DOMINIK MARCZUK ``AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL DOMINIK MARCZUK BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

#Ported to python by initrl.

import random
import sys
import curses
import copy
import time

screen = curses.initscr()

mapWidth = 80
mapHeight = 24
playerPosX = 10
playerPosY = 10

class cell:
    def __init__(self):
        self.fov = False
        self.transparent = False
        self.walkable = False

class mainmap:
    def __init__ (self, w, h):
        self.width = w
        self.height = h
        self.nbcells = w * h
        self.cells = []
        for i in xrange(self.nbcells + 1):
            self.cells.append(cell())
    def generate (self):
        for i in xrange(self.nbcells + 1):
            if random.randint(0, 100) > 1:
                self.cells[i].transparent = True
                self.cells[i].walkable = True
            else:
                self.cells[i].transparent = False
                self.cells[i].walkable = False
            self.cells[i].fov = False
    def displayTile(self, idx):
        if self.cells[idx].walkable:
            if self.cells[idx].fov == True:
                c = '.'
            else:
                c = ' '
        else:
            if self.cells[idx].fov == True:
                c = '#'
            else:
                c = '?'
        if playerPosY * mapWidth + playerPosX == idx:
            c = '@'
        return c

#the fov itself

class MRPAS:
    def computeQuadrant (self, m, playerX, playerY, maxRadius, lightWalls, dx, dy):
        startAngle = [None] * 100
        endAngle = [None] * 100
        #octant: vertical edge:
        iteration = 1
        done = False
        totalObstacles = 0
        obstaclesInLastLine = 0
        minAngle = 0.0
        x = 0.0
        y = playerY + dy
        #do while there are unblocked slopes left and the algo is within
        # the map's boundaries
        #scan progressive lines/columns from the PC outwards
        if y < 0 or y >= m.height:
            done = True
        while not done:
            #process cells in the line
            slopesPerCell = 1.0 / (iteration + 1);
            halfSlopes = slopesPerCell * 0.5
            processedCell = int(minAngle / slopesPerCell)
            minx = max(0, playerX - iteration)
            maxx = min(m.width - 1, playerX + iteration)
            done = True
            x = playerX + (processedCell * dx)
            while x >= minx and x <= maxx:
                #calculate slopes per cell
                c = x + (y * m.width)
                visible = True
                startSlope = processedCell * slopesPerCell
                centreSlope = startSlope + halfSlopes
                endSlope = startSlope + slopesPerCell
                if obstaclesInLastLine > 0 and m.cells[int(c)].fov == False:
                    idx = 0
                    while visible and idx < obstaclesInLastLine:
                        if m.cells[int(c)].transparent == True:
                            if centreSlope > startAngle[idx] and centreSlope < \
                                                                  endAngle[idx]:
                                visible = False
                        else:
                            if startSlope >= startAngle[idx] and endSlope <= endAngle[idx]:
                                visible = False
                        if visible and (not m.cells[c - (m.width * dy)].fov or\
                                  not m.cells[c - (m.width * dy)].transparent)\
                                  and (x - dx >= 0 and x - dx < m.width and\
                                  (m.cells[c - (m.width * dy) - dx].fov == False\
                                   or not m.cells[c - (m.width * dy) - dx].\
                                   transparent)):
                            visible = False
                        idx += 1
                if visible:
                    m.cells[int(c)].fov = True
                    done = False
                    #if the cell is opaque, block the adjacent slopes
                    if not m.cells[int(c)].transparent:
                        if minAngle >= startSlope:
                            minAngle = copy.deepcopy(endSlope)
                        else:
                            startAngle[totalObstacles] = copy.deepcopy(startSlope)
                            endAngle[totalObstacles] = copy.deepcopy(endSlope)
                            totalObstacles += 1
                        if (not lightWalls):
                            m.cells[int(c)].fov = False
                processedCell += 1
                x += dx
            if iteration == maxRadius:
                done = True
            iteration += 1
            obstaclesInLastLine = copy.deepcopy(totalObstacles);
            y += dy
            if y < 0 or y >= m.height:
                done = True
            if minAngle == 1.0:
                done = True
        
        #octant: horizontal edge
        iteration = 1 #iteration of the algo for this octant
        done = False
        totalObstacles = 0
        obstaclesInLastLine = 0
        minAngle = 0.0
        x = (playerX + dx) #the outer slope's coordinates (first processed line)
        y = 0
        #do while there are unblocked slopes left and the algo is within the map's boundaries
        #scan progressive lines/columns from the PC outwards
        if  x < 0 or x >= m.width:
            done = True
        while not done:
            #process cells in the line
            slopesPerCell = 1.0 / (iteration + 1)
            halfSlopes = slopesPerCell * 0.5
            processedCell = int(minAngle / slopesPerCell)
            miny = max(0, playerY - iteration)
            maxy = min(m.height - 1, playerY + iteration);
            done = True
            y = playerY + (processedCell * dy)
            while y >= miny and y <= maxy:
                #calculate slopes per cell
                c = x + (y * m.width)
                visible = True
                startSlope = (processedCell * slopesPerCell)
                centreSlope = startSlope + halfSlopes
                endSlope = startSlope + slopesPerCell
                if obstaclesInLastLine > 0 and m.cells[int(c)].fov == False:
                    idx = 0
                    while visible and idx < obstaclesInLastLine:
                        if m.cells[int(c)].transparent == True:
                            if centreSlope > startAngle[idx] and centreSlope < \
                                endAngle[idx]:
                                visible = False
                        else:
                            if startSlope >= startAngle[idx] and endSlope <= endAngle[idx]:
                                visible = False
                        if visible and (m.cells[c - dx].fov == False or\
                                not m.cells[c - dx].transparent) and\
                                (y - dy >= 0 and y - dy < m.height and (m.cells[c - \
                                (m.width * dy) - dx].fov == False or not m.cells[c - \
                                (m.width * dy) - dx].transparent)):
                            visible = False
                        idx += 1
                if visible:
                    m.cells[int(c)].fov = True
                    done = False
                    #if the cell is opaque, block the adjacent slopes
                    if not m.cells[int(c)].transparent:
                        if minAngle >= startSlope:
                            minAngle = copy.deepcopy(endSlope)
                        else:
                            startAngle[totalObstacles] = copy.deepcopy(startSlope)
                            endAngle[totalObstacles] = copy.deepcopy(endSlope)
                            totalObstacles += 1
                        if not lightWalls:
                            m.cells[int(c)].fov = False
                processedCell += 1
                y += dy
            if iteration == maxRadius:
                done = True
            iteration += 1
            obstaclesInLastLine = copy.deepcopy(totalObstacles);
            x += dx
            if x < 0 or x >= m.width:
                done = True
            if minAngle == 1.0:
                done = True

    def computeFov (self, m, playerX, playerY, maxRadius, lightWalls):
        #first, zero the FOV map
        for c in xrange(m.nbcells + 1):
            m.cells[c].fov = False
        #set PC's position as visible
        m.cells[playerX + (playerY * m.width)].fov = True
        #compute the 4 quadrants of the map
        self.computeQuadrant(m, playerX, playerY, maxRadius, lightWalls, 1, 1);
        self.computeQuadrant(m, playerX, playerY, maxRadius, lightWalls, 1, -1);
        self.computeQuadrant(m, playerX, playerY, maxRadius, lightWalls, -1, 1);
        self.computeQuadrant(m, playerX, playerY, maxRadius, lightWalls, -1, -1);

#LET'S DO IT!
m = mainmap(mapWidth, mapHeight)
m.generate();
fov = MRPAS()
key = "0"
x1, y1 = playerPosX, playerPosY
stime = time.time()
while key != "q":
    screen.refresh()
    fov.computeFov(m, playerPosX, playerPosY, 100 , True)
    for j in xrange(mapHeight - 1):
        for i in xrange(mapWidth - 1):
            screen.addstr(j, i, m.displayTile(j * mapWidth + i))
    try:
        key = chr(screen.getch())
    except:
        curses.endwin()
        sys.exit(0)
    if key == "8" or key == "k" or key == 259:
        x1 -= 1
    elif key == "2" or key == "j" or key == 258:
        x1 += 1
    elif key == "4" or key == "h" or key == 260:
        y1 -= 1
    elif key == "6" or key == "l" or key == 261:
        y1 += 1
    elif key == "7" or key == "y" or key == 262:
        x1 -= 1
        y1 -= 1
    elif key == "9" or key == "u" or key == 339:
        x1 -= 1
        y1 += 1
    elif key == "1" or key == "b" or key == 360:
        x1 += 1
        y1 -= 1
    elif key == "3" or key == "n" or key == 338:
        x1 += 1
        y1 += 1
    if m.cells[x1 * mapWidth + y1].walkable and \
    x1 >= 0 and x1 < mapHeight - 1 and y1 >= 0 and y1 < mapWidth - 1:
        playerPosX = y1
        playerPosY = x1
    else:
        y1 = playerPosX
        x1 = playerPosY
etime = time.time()
curses.endwin()
ttime = etime - stime
print "Start: %f, End: %f, Running: %f seconds." % (stime,etime,ttime)