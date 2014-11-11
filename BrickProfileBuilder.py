#!/usr/bin/env python
#-*- coding: utf-8 -*-

import rospy
from geometry_msgs.msg import Twist
import numpy as np
import time
import sys
from scipy import integrate

class Profile(object):
    def __init__(self, rate, max_linear_velocity, max_angular_velocity):
        self.rate = float(rate)  # [Hz]
        self.sample_time = 1.0 / rate  # [s]

        self.max_linear_velocity = max_linear_velocity
        self.max_angular_velocity = max_angular_velocity



class Bricks(object):
    def __init__(self, profile):
        self.profile = profile

    def calc_samples(self, duration):
        return duration / self.profile.sample_time

    def evenMaxSamples(self, *args):
        args = list(args)
        max_samples = max(map(len, args))
        for idx, sample_line in enumerate(args):
            remaining_samples = max_samples - len(sample_line)
            fill_data = np.zeros((remaining_samples), np.float)
            args[idx] = np.append(sample_line, fill_data)
        return args


    def sin(self, start, stop, duration):
        return np.sin(np.linspace(start, stop, self.calc_samples(duration)))

    def sin_t(self, A, f, phi, T):
        #return np.sin(np.linspace(0, np.pi*2 * f*T, self.calc_samples(T)))
        return A * self.sin(phi, f*np.pi*2*T+phi, T)

    def cos(self, start, stop, duration):
        return np.cos(np.linspace(start, stop, self.calc_samples(duration)))

    def lin(self, duration, velocity=1):
        return np.linspace(velocity, velocity, self.calc_samples(duration))

    def lin_dist(self, distance, duration):
        speed = float(distance) / float(duration)
        print speed
        return self.lin(duration) * speed

    def acc(self, velocity_start, velocity_end, duration):
        if velocity_start < velocity_end:
            sin_intv = self.sin(-np.pi/2, np.pi/2, duration)
            velocity_low, velocity_hi = velocity_start, velocity_end
        else:
            sin_intv = self.sin(np.pi/2, np.pi*3/2, duration)
            velocity_low, velocity_hi = velocity_end, velocity_start
        return (sin_intv + 1) / 2 * (velocity_hi - velocity_low) + velocity_low

    def circular_path_parameter(self, duration, radius, phi):

        theta = phi / (np.pi + duration / 1.2)

        #dphi = phi / self.calc_samples(np.pi + duration / 1.2)
        #theta = dphi / self.profile.sample_time
        velocity = radius * theta
        return velocity, theta

    def circular_path(self, duration, radius, phi):
        # FIXME: hardcoded...
        velocity_start = 0
        velocity_end = 0


        TLX = np.array([], np.float)
        TLTH = np.array([], np.float)

        vx, vtheta = self.circular_path_parameter(duration=duration, radius=radius, phi=phi)

        # TODO add description...
        if phi < 0:
            vx*=-1

        if radius < 0:
            vtheta *= -1

        # accelerate
        TLX = np.append(TLX, self.acc(velocity_start=velocity_start, velocity_end=vx, duration=duration*0.1))
        TLTH = np.append(TLTH, self.acc(velocity_start=velocity_start, velocity_end=vtheta, duration=duration*0.1))

        # circular movement
        TLX = np.append(TLX, self.lin(velocity=vx, duration=duration*0.8))
        TLTH = np.append(TLTH, self.lin(velocity=vtheta, duration=duration*0.8))

        # decelerate
        TLX = np.append(TLX, self.acc(velocity_start=vx, velocity_end=velocity_end, duration=duration*0.1))
        TLTH = np.append(TLTH, self.acc(velocity_start=vtheta, velocity_end=velocity_end, duration=duration*0.1))

        return TLX, TLTH



class GeneralMovement(object):
    def __init__(self, profile):
        self.profile = profile

    def move_linear(self, speed, duration):
        return

class BoringMovement(object):
    def __init__(self, profile):
        self.profile = profile


class ROSBridge(object):
    class Dummy(object):
        pass

    def __init__(self, profile, fakerun=False):
        self.profile = profile

        if not fakerun:
            rospy.init_node('VID_TEST')
            self.pub = rospy.Publisher('/base_controller/command_direct', Twist)
        else:
            self.pub = ROSBridge.Dummy()
            self.pub.publish = self.print_fakerun

    def print_fakerun(self, msg):
        print msg
        print '-'*50

    def exec_timeline(self, timeline):

        for step in range(max([len(timeline['x']), len(timeline['y']), len(timeline['th'])])):
            twist = Twist()
            if step < len(timeline['x']):
                twist.linear.x = timeline['x'][step]
            if step < len(timeline['y']):
                twist.linear.y = timeline['y'][step]
            if step < len(timeline['th']):
                twist.angular.z = timeline['th'][step]

            self.pub.publish(twist)
            time.sleep(self.profile.sample_time)


if __name__ == '__main__':

    is_fakerun = True if '-fakerun' in sys.argv else False
    is_plot = True if '-plot' in sys.argv else False
    is_ros = True if '-ros' in sys.argv else False


    TLX = np.array([], np.float)
    TLY = np.array([], np.float)
    TLTH = np.array([], np.float)

    profile = Profile(rate=100, max_linear_velocity=0.2, max_angular_velocity=0.4)
    bricks = Bricks(profile)

    boring = BoringMovement(profile)

    # wait 0.5 sec
    TLX = np.append(TLX, bricks.lin(duration=0.5, velocity=0))

    # sync lines
    TLX, TLY, TLTH = bricks.evenMaxSamples(TLX, TLY, TLTH)


    # KREISBAHN
    ############

    # vor links
    tlx, tlth = bricks.circular_path(radius=0.5, phi=np.pi/2, duration=6)
    TLX = np.append(TLX, tlx)
    TLTH = np.append(TLTH, tlth)
    '''
    # rück links
    tlx, tlth = bricks.circular_path(radius=-0.5, phi=np.pi/2, duration=6)
    TLX = np.append(TLX, tlx)
    TLTH = np.append(TLTH, tlth)
    '''

    '''    # vor rechts
    tlx, tlth = bricks.circular_path(radius=0.5, phi=-np.pi/2, duration=6)
    TLX = np.append(TLX, tlx)
    TLTH = np.append(TLTH, tlth)

    # rück rechts
    tlx, tlth = bricks.circular_path(radius=-0.5, phi=-np.pi/2, duration=6)
    TLX = np.append(TLX, tlx)
    TLTH = np.append(TLTH, tlth)
    '''


    # sync lines
    TLX, TLY, TLTH = bricks.evenMaxSamples(TLX, TLY, TLTH)



    TIMELINE = dict()
    TIMELINE['x'] = TLX
    TIMELINE['y'] = TLY
    TIMELINE['th'] = TLTH

    if is_ros:
        bridge = ROSBridge(profile, fakerun=is_fakerun)
        bridge.exec_timeline(TIMELINE)

    if is_plot:
        import matplotlib.pyplot as plt
        import scipy

        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, ncols=1)


        TLX, TLY, TLTH = bricks.evenMaxSamples(TLX, TLY, TLTH)
        max_samples = max([len(TLX), len(TLY), len(TLTH)])
        xdata = np.linspace(0, profile.sample_time * max_samples, max_samples)

        TLXD = np.array([0], np.float)
        TLYD = np.array([0], np.float)
        TLTHD = np.array([0], np.float)

        TLXD = np.append(TLXD, integrate.cumtrapz(TLX, xdata))
        TLYD = np.append(TLYD, integrate.cumtrapz(TLY, xdata))
        TLTHD = np.append(TLTHD, integrate.cumtrapz(TLTH, xdata))

        ax1.plot(xdata, TLXD)
        ax1.plot(xdata, TLYD)
        ax1.plot(xdata, TLTHD)
        ax1.legend(['X', 'Y', 'Theta'])
        ax1.set_title('Distance')

        ##################################################


        ax2.plot(xdata, TLX)
        ax2.plot(xdata, TLY)
        ax2.plot(xdata, TLTH)
        ax2.legend(['X', 'Y', 'Theta'])
        ax2.set_title('Velocity')

        ##################################################


        TLXA = np.array([0], np.float)
        TLYA = np.array([0], np.float)
        TLTHA = np.array([0], np.float)

        TLXA = np.append(TLXA, scipy.diff(TLX))
        TLYA = np.append(TLYA, scipy.diff(TLY))
        TLTHA = np.append(TLTHA, scipy.diff(TLTH))

        ax3.plot(xdata, TLXA)
        ax3.plot(xdata, TLYA)
        ax3.plot(xdata, TLTHA)
        ax3.legend(['X', 'Y', 'Theta'])
        ax3.set_title('Acceleration')


        fig, (ax1) = plt.subplots(nrows=1, ncols=1)
        TLTHDS = np.sin(TLTHD)
        TLTHDC = np.cos(TLTHD)
        TLPX = TLXD * TLTHDS
        TLPY = TLXD * TLTHDC
        ax1.plot(TLPX, TLPY)
        ax1.set_xlabel('x [m]')
        ax1.set_ylabel('y [m]')
        ax1.legend(['Path'])

        plt.axis('equal')


        ##################################################
        # TESTING AREA
        ##################################################


        fig, (ax1) = plt.subplots(nrows=1, ncols=1)

        phi = np.pi/2
        R = 0.5
        T = 6

        T1 = T*0.1
        T2 = T*0.8
        T3 = T*0.1


        #s = 2 * np.pi * R / phi
        s = R * phi

        v_max = s / (2 * np.pi + 0.2*T) + s / T*0.8
        print v_max

        magic = 12#2.22#np.pi * 2 / 3

        #v_max = R * phi * magic / T
        print np.pi * 2 / 3
        print v_max

        #s = R * phi
        #v_max = s / T

        vdata = np.array([], np.float)
        vdata = np.append(vdata, bricks.acc(velocity_start=0, velocity_end=v_max, duration=T1))
        vdata = np.append(vdata, bricks.lin(velocity=v_max, duration=T2))
        vdata = np.append(vdata, bricks.acc(velocity_start=v_max, velocity_end=0, duration=T3))

        anz_samples = bricks.calc_samples(T)
        tdata = np.linspace(0, profile.sample_time * anz_samples, anz_samples)

        sdata = np.array([0], np.float)
        sdata = np.append(sdata, integrate.cumtrapz(vdata, tdata))


        xdata = R * np.cos(sdata)
        ydata = R * np.sin(sdata)
        ax1.plot(xdata, ydata, '-', color=(0, 0, 0))

        xdata = R * np.cos(sdata[anz_samples*0.0:anz_samples*0.1])
        ydata = R * np.sin(sdata[anz_samples*0.0:anz_samples*0.1])
        ax1.plot(xdata, ydata, 'rx-')

        xdata = R * np.cos(sdata[anz_samples*0.1:anz_samples*0.9])
        ydata = R * np.sin(sdata[anz_samples*0.1:anz_samples*0.9])
        ax1.plot(xdata, ydata, 'yx-')

        xdata = R * np.cos(sdata[anz_samples*0.9:anz_samples*1])
        ydata = R * np.sin(sdata[anz_samples*0.9:anz_samples*1])
        ax1.plot(xdata, ydata, 'gx-')



        plt.axis('equal')

        plt.tight_layout()
        plt.show()