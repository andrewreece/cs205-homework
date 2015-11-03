import sys
import os.path
sys.path.append(os.path.join('..', 'util'))

import set_compiler
set_compiler.install()

import pyximport
pyximport.install()

import numpy as np
from timer import Timer
from animator import Animator
from physics import update, preallocate_locks

import matplotlib.pyplot as plt

def randcolor():
    return np.random.uniform(0.0, 0.89, (3,)) + 0.1

if __name__ == '__main__':
    num_balls = 500
    radius = 0.01
    positions = np.random.uniform(0 + radius, 1 - radius,
                                  (num_balls, 2)).astype(np.float32)

    # make a hole in the center
    while True:
        distance_from_center = np.sqrt(((positions - 0.5) ** 2).sum(axis=1))
        mask = (distance_from_center < 0.25)
        num_close_to_center = mask.sum()
        if num_close_to_center == 0:
            # everything is out of the center
            break
        positions[mask, :] = np.random.uniform(0 + radius, 1 - radius,
                                               (num_close_to_center, 2)).astype(np.float32)

    velocities = np.random.uniform(-0.25, 0.25,
                                   (num_balls, 2)).astype(np.float32)

    # Initialize grid indices:
    #
    # Each square in the grid stores the index of the object in that square, or
    # -1 if no object.  We don't worry about overlapping objects, and just
    # store one of them.
    grid_spacing = radius / np.sqrt(2.0)
    grid_size = int((1.0 / grid_spacing) + 1)
    grid = - np.ones((grid_size, grid_size), dtype=np.uint32)
    grid[(positions[:, 0] / grid_spacing).astype(int),
         (positions[:, 1] / grid_spacing).astype(int)] = np.arange(num_balls)

    # A matplotlib-based animator object
    animator = Animator(positions, radius * 2)

    # simulation/animation time variablees
    physics_step = 1.0 / 100  # estimate of real-time performance of simulation
    anim_step = 1.0 / 30  # FPS
    total_time = 0

    frame_count = 0

    # preallocate locks for objects
    locks_ptr = preallocate_locks(num_balls)

    chunk = num_balls/4
    nthread = 1
    SFPS = []
    ct = 0

    def rot(n,x,y,rx,ry):
        if (ry == 0):
            if (rx == 1):
                x = n-1 - x
                y = n-1 - y
            

            #Swap x and y
            t = x
            x = y
            y = t
        return x,y

    #convert (x,y) to d
    def xy2d (n, x, y):
        s = n/2
        d = 0
        while s > 0:
            rx = int(x & s > 0)
            ry = int(y & s > 0)
            d += s * s * ((3 * rx) ^ ry)
            x,y = rot(s, x, y, rx, ry)
            s /= 2
        return d
    
    while True:
        with Timer() as t:
            update(positions, velocities, grid,
                   radius, grid_spacing, locks_ptr,
                   physics_step, nthread, chunk)

        # udpate our estimate of how fast the simulator runs
        physics_step = 0.9 * physics_step + 0.1 * t.interval
        total_time += t.interval

        frame_count += 1
        if total_time > anim_step:
            animator.update(positions)
            print("{} simulation frames per second".format(frame_count / total_time))
            SFPS.append(frame_count / total_time)
            frame_count = 0
            total_time = 0
            # SUBPROBLEM 3: sort objects by location.  Be sure to update the
            # grid if objects' indices change!  Also be sure to sort the
            # velocities with their object positions!
            gridx = (positions[:, 0] / grid_spacing).astype(int)
            gridy = (positions[:, 1] / grid_spacing).astype(int)
            hilberted = np.argsort([xy2d(grid_size,x,y) for x,y in zip(gridx,gridy)])
            positions = positions[hilberted,:]
            gridx = (positions[:, 0] / grid_spacing).astype(int)
            gridy = (positions[:, 1] / grid_spacing).astype(int)
            grid[gridx,gridy] = np.arange(num_balls)
            velocities[:] = velocities[hilberted,:]
           
        # plotting FPS histograms
        if ct > 100000:
            fig, ax = plt.subplots()
            ax.hist(SFPS, bins=100)
            ax.set_title("Histogram of simulation FPS, {} threads".format(nthread), fontsize=16)
            ax.set_xlabel("Simulation Frames Per Second", fontsize=14)
            ax.set_ylabel("Frequency", fontsize=14)
            ax.set_xlim([0,10000])
            fig.savefig('threads{}.png'.format(nthread))
            
            break

        ct += 1 # this is so we know when to break after enough time to collect a good histogram