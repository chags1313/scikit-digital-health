from PfyMU.features import *

from PfyMU.tests.features.conftest import TestFeature


class TestMean(TestFeature):
    feature = Mean()


class TestMeanCrossRate(TestFeature):
    feature = MeanCrossRate()


class TestStdDev(TestFeature):
    feature = StdDev()


class TestSkewness(TestFeature):
    feature = Skewness()


class TestKurtosis(TestFeature):
    feature = Kurtosis()


class TestSignalEntropy(TestFeature):
    feature = SignalEntropy()


class TestSampleEntropy(TestFeature):
    feature = SampleEntropy(m=4, r=1.0)


class TestPermutationEntropy(TestFeature):
    feature = PermutationEntropy(order=4, delay=1, normalize=False)


class TestDominantFrequency(TestFeature):
    feature = DominantFrequency(low_cutoff=0.0, high_cutoff=12.0)


class TestDominantFrequencyValue(TestFeature):
    feature = DominantFrequencyValue(low_cutoff=0.0, high_cutoff=12.0)


class TestPowerSpectralSum(TestFeature):
    feature = PowerSpectralSum(low_cutoff=0.0, high_cutoff=12.0)


class TestSpectralFlatness(TestFeature):
    feature = SpectralFlatness(low_cutoff=0.0, high_cutoff=12.0)


class TestSpectralEntropy(TestFeature):
    feature = SpectralEntropy(low_cutoff=0.0, high_cutoff=12.0)
