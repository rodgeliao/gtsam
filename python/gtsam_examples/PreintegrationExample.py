"""
A script validating the Preintegration of IMU measurements
"""

import math
import matplotlib.pyplot as plt
import numpy as np

from mpl_toolkits.mplot3d import Axes3D

import gtsam
from gtsam_utils import plotPose3

IMU_FIG = 1
POSES_FIG = 2

class PreintegrationExample(object):

    @staticmethod
    def defaultParams(g):
        """Create default parameters with Z *up* and realistic noise parameters"""
        params = gtsam.PreintegrationParams.MakeSharedU(g)
        kGyroSigma = math.radians(0.5) / 60  # 0.5 degree ARW
        kAccelSigma = 0.1 / 60  # 10 cm VRW
        params.gyroscopeCovariance = kGyroSigma ** 2 * np.identity(3, np.float)
        params.accelerometerCovariance = kAccelSigma ** 2 * np.identity(3, np.float)
        params.integrationCovariance = 0.0000001 ** 2 * np.identity(3, np.float)
        return params

    def __init__(self, twist=None, bias=None, dt=1e-2):
        """Initialize with given twist, a pair(angularVelocityVector, velocityVector)."""
        
        # setup interactive plotting
        plt.ion()

            # Setup loop as default scenario
        if twist is not None:
            (W, V) = twist
        else:
            # default = loop with forward velocity 2m/s, while pitching up
            # with angular velocity 30 degree/sec (negative in FLU)
            W = np.array([0, -math.radians(30), 0])
            V = np.array([2, 0, 0])

        self.scenario = gtsam.ConstantTwistScenario(W, V)
        self.dt = dt

        self.maxDim = 5
        self.labels = list('xyz')
        self.colors = list('rgb')

        # Create runner
        self.g = 10  # simple gravity constant
        self.params = self.defaultParams(self.g)
        ptr = gtsam.ScenarioPointer(self.scenario)

        if bias is not None:
            self.actualBias = bias
        else:
            accBias = np.array([0, 0.1, 0])
            gyroBias = np.array([0, 0, 0])
            self.actualBias = gtsam.ConstantBias(accBias, gyroBias)

        self.runner = gtsam.ScenarioRunner(ptr, self.params, self.dt, self.actualBias)

    def plotImu(self, t, measuredOmega, measuredAcc):
        plt.figure(IMU_FIG)

        # plot angular velocity    
        omega_b = self.scenario.omega_b(t)
        for i, (label, color) in enumerate(zip(self.labels, self.colors)):
            plt.subplot(4, 3, i + 1)
            plt.scatter(t, omega_b[i], color='k', marker='.')
            plt.scatter(t, measuredOmega[i], color=color, marker='.')
            plt.xlabel('angular velocity ' + label)

        # plot acceleration in nav
        acceleration_n = self.scenario.acceleration_n(t)
        for i, (label, color) in enumerate(zip(self.labels, self.colors)):
            plt.subplot(4, 3, i + 4)
            plt.scatter(t, acceleration_n[i], color=color, marker='.')
            plt.xlabel('acceleration in nav ' + label)

        # plot acceleration in body
        acceleration_b = self.scenario.acceleration_b(t)
        for i, (label, color) in enumerate(zip(self.labels, self.colors)):
            plt.subplot(4, 3, i + 7)
            plt.scatter(t, acceleration_b[i], color=color, marker='.')
            plt.xlabel('acceleration in body ' + label)

        # plot actual specific force, as well as corrupted
        actual = self.runner.actualSpecificForce(t)
        for i, (label, color) in enumerate(zip(self.labels, self.colors)):
            plt.subplot(4, 3, i + 10)
            plt.scatter(t, actual[i], color='k', marker='.')
            plt.scatter(t, measuredAcc[i], color=color, marker='.')
            plt.xlabel('specific force ' + label)

    def plotGroundTruthPose(self, t):
        # plot ground truth pose, as well as prediction from integrated IMU measurements
        actualPose = self.scenario.pose(t)
        plotPose3(POSES_FIG, actualPose, 0.3)
        t = actualPose.translation()
        self.maxDim = max([abs(t[0]), abs(t[1]), abs(t[2]), self.maxDim])
        ax = plt.gca()
        ax.set_xlim3d(-self.maxDim, self.maxDim)
        ax.set_ylim3d(-self.maxDim, self.maxDim)
        ax.set_zlim3d(-self.maxDim, self.maxDim)

        plt.pause(0.01)

    def run(self):
        # simulate the loop
        T = 12
        for i, t in enumerate(np.arange(0, T, self.dt)):
            measuredOmega = self.runner.measuredAngularVelocity(t)
            measuredAcc = self.runner.measuredSpecificForce(t)
            if i % 25 == 0:
                self.plotImu(t, measuredOmega, measuredAcc)
                self.plotGroundTruthPose(t)
                pim = self.runner.integrate(t, self.actualBias, True)
                predictedNavState = self.runner.predict(pim, self.actualBias)
                plotPose3(POSES_FIG, predictedNavState.pose(), 0.1)

        plt.ioff()
        plt.show()

if __name__ == '__main__':
    PreintegrationExample().run()
