# Tiles Game Demo Intan Interface
This is the Intan Interface for the white tiles demo for ECE202 Group 7. The purpose of this interface is to connect to the Intan software, read the EMG data frome **TWO** channels and convert to game controls, i.e. left arm = move left, right arm = move right.  

### Task List:
* [x] Read from Intan
* [x] Calibration
    * Determine resting potential range
    * Determine threshold for "flexing" potential minimum
* [x] Read from 2 channels (Done via multiprocessing and 2 Intan Softwares)
* [x] Link to game movements

### Sample Waveforms:
<div style="display: flex;">
    <div>
        Figure 1: Resting Waveform
        <img src="waveforms\resting.png">
    </div>
    <div>
        Figure 2: Flexing Waveform
        <img src="waveforms\flexing.png">
    </div>
</div>

### Calibration:
#### Method 2: CWT Frequency-Time Power Mean Analysis
The Spectrogram used for Lab 5 would not work for python when I tried implementing it. After a couple of hours of researching, I found a useful method: **cwt**, from the `PyWavelets` library. Countinuous Wavelet Transform (CWT) is used  because we would like to classify flexing depending on the frequency of high power signals. If we refer back to Figure 2, we can observe higher peaks compared to Figure 1 for resting. This decision was made after the inconsistency and inaccuracy of method 1, which was primarily caused by the presence of low potential points in the waveform in both states. 

Our objective is to effectively measure the frequency of high power signals per time period and classify it as flexing or resting based whether it passes a threshold. After some research, it is found that CWT has high performance results and is effective for our objective in detecting the presence of high power signals at higher frequencies. I used this to help understand and implement the CWT components: https://www.youtube.com/watch?v=qoMDpSatG7M. All references for research are provided in the [references](#references).

**Choosing the correct wavelet:**
A graph of each different wavelets are provided. The same recording data and timestamps were used for each with 60% resting and 40% flexing. The recording used was pre-captured and is the same as the EMG recording used for Lab 5 W2-5pm, provided in the reference. The frequency range was determined by `np.arange(1, 128, 4)` which gives a total of 32 frequency entries. This was the set of parameters that gave the best and clearest plot. After further testing, this scale is the best and focusing the frequency at 25Hz seems to the safest (observe the last 2 wavelet spectrograms for a different recording).
    <details>
        <summary>Wavelets (Click to View Plots)</summary>
        <ul>
            <il><img src="wavelets\cgau1.png" alt="cgau1"></li>
            <il><img src="wavelets\cgau2.png" alt="cgau2"></li>
            <il><img src="wavelets\cgau4.png" alt="cgau4"></li>
            <il><img src="wavelets\cgau5.png" alt="cgau5"></li>
            <il><img src="wavelets\cgau6.png" alt="cgau6"></li>
            <il><img src="wavelets\cmor.png" alt="cmor"></li>
            <il><img src="wavelets\fbsp.png" alt="fbsp"></li>
            <il><img src="wavelets\gaus1" alt="gaus1"></li>
            <il><img src="wavelets\gaus2.png" alt="gaus2"></li>
            <il><img src="wavelets\mexh.png" alt="mexh"></li>
            <il><img src="wavelets\morl.png" alt="morl"></li>
            <il><img src="wavelets\shan.png" alt="shannon"></li>
            <il><img src="wavelets\record2rest.png" alt="record2rest"></li>
            <il><img src="wavelets\record2flex.png" alt="record2flex"></li>
        </ul>
    </details>
Based on these plots, `mexh` waveform provides the clearest distinction betwen resting and flexing, specifically at high frequency. This will be used to model all calibration and measuring. 

The calibration is done by computing the CWT for the resting and flexing and obtaining the mean power for each sample period. The threshold will be halfway between the two. If the results for this threshold prove dissatisfactory, we'll lower the percentage in the same manner as method 1. For Trials 1-3, the calibration is recorded from ~00:26 to ~00:31 for resting, ~00:36 to ~01:00 for flexing. From ~00:36 to ~11:00, 4 second periods were recorded to classify if it's flexing or resting and compare with the actual results `[flex, flex, flex, flex, rest]`
Trial 4 was purposely made inaccurate (~00:25). Trial 5 was calibrated to the same range as Trial 4, but with smaller sample periods for testing, specifically 24 samples of 1 second.

| Trial | Resting Avg | Flexing Avg | Threshold | Success Rate |
| ----- | ----------- | ----------- | --------- | ------------ |
|   1   |  217.64827  |  1104.6303  | 661.13933 |     6/6      |
|   2   |  218.29066  |  1095.7019  | 656.99629 |     6/6      |
|   3   |  217.64827  |  1104.7583  | 661.20333 |     6/6      |
|   4   |  225.05978  |  1104.7583  | 594.26345 |     6/6      |
|   5   |  221.00389  |  1072.8995  | 646.95171 |    20/24*    |

\* *Note: Trial 5 ended the testing at 00:54, for the 24 samples of "1 second". While observing the tests, despite setting `sleep(1)`, it was stoping at 800ms (0.8s) on intan software. This may be due to latency. The actual result was `[True] * 15 + [False] * 9` for each second as flexing occurs until ~00:50 in the recording. If we were to consider this mismatch for this, the results may be near 100% success rate if not at.*

Immediately we can see a clearer distinction between resting and flexing state. The success rate is also much higher (100%) for each trial except for trial 5 (as mentioned in the disclaimer). For this reason, we can conclude that this method is reliable for both calibration and measuring.

**Live Measuring**  
Live measuring of an electrode will be done in 0.25 second recording periods. Since we have two electrodes, we will need to switch channels every 0.25 seconds of recording from one electrode to the other. This will give ~500ms recording periods for one full measurement. However, given a much smaller recording period (compared to 1 second above), the accuracy will be more susceptible to noise. To fix this, we'll adjust and test different threshold percentages, i.e. flexing detected is when the mean of the recorded period is > percentage of the distance between the calibrated resting and flexing mean. The value at this percentage will be determined at calibration. 

For this test, we are still using only one electrode. There will be 80 tests of 250ms, for a total of 20 seconds. We will be using the Lab5 Tr9-11a recording. The calibration is performed for 3 seconds each starting at ~00:02.

| Trial | Threshold % | Success Rate |
| ----- | ----------- | ------------ |
|   1   |     50%     |    56/80     |
|   2   |     25%     |    49/80     |
|   3   |     75%     |    79/80     |

Given a threshold % of 75% gave the best results, this will be used for all live recordings. Moreoever, observation in the detection of flexing notes the single incorrect classification occurs at either the start or end of a flexing/resting period in the recording. Contrarily, the other %'s give misclassifications in the middle of a flexing/resting period, especially during rest which is likely due to noise.

#### Method 1: Standard Deviation
**Notes**: Not reliable due to regular lower potentials in the waveform. Notice in both sets of trials, the standard deviation of thee flexing remained relatively close to the resting. This means at higher sample rates, the standard deviation is more likely to be incorrectly classified. This can be shown with association such that in these trial sets, the sample time was 5 seconds (the same as the calibration time), yet it still could not achieve 100% accuracy when needed. This same situation occurs with mean as it is related.

Calibration detects the standard deviation of potential of both resting and flexing. A lower threshold of which the standard deviation must exceed to be considered "flexing" is computed as a percentage between the two state's standard deviation. Two version of standard deviation were calculated, tested, and compared under three trials of the same sample EMG recording:

Standard deviation was picked initially based on the observed EMG waveforms as showin Figure 1 and 2. In figure 1, we can observe regular and smaller potential variance such that a pattern can be recognized. Figure 2 has more chaotic variance in the potentials such that we cannot observe a regular pattern. Visiually, it appears that the standard deviation is higher for the flexing state.

Two cases for computing the standard deviationw as considered: raw and absolute value. For each, we use the pre-recorded EMG data in the [references](#references). Calibration is recorded from ~00:25 to ~00:30 for resting, ~00:30 to ~00:35 for flexing. From ~00:35 to ~00:55, 5 second periods were recorded to classify if it's flexing or resting and compare with the actual results `[flex, flex, flex, rest]`

1. `np.abs(data)`, where all potentials considered were absolute valued to find the std. dev. Trials 1 and 2 computes the threshold at 50%. Trials 3 and 4 computes the threshold at 25% and 10% respectively. This decision was made on the uniformity (specifically the observable pattern) such that we can expect resting standard deviation to always be relatively close to the calibrated resting standard deviation with some error.

| Trial | Resting STD | Flexing STD | Threshold [\%] | Success Rate |
| ----- | ----------- | ----------- | -------------- | ------------ |
|   1   |  242.62885  |  267.21950  | 254.92418 [50\%] |     2/4      |
|   2   |  242.58384  |  266.63958  | 254.61171 [50\%] |     3/4      |
|   3   |  242.75175  |  268.25693  | 249.12804 [25\%] |     3/4      |
|   4   |  243.20143  |  266.22612  | 245.50391 [10\%] |     3/4      |

2. Just `data` by itself were considered for the std. dev. Other parameters for each trial are the same as above.
   
| Trial | Resting STD | Flexing STD | Threshold [\%] | Success Rate |
| ----- | ----------- | ----------- | -------------- | ------------ |
|   1   |  453.70970  |  476.00338  | 464.85654 [50\%] |     1/4      |
|   1   |  453.53124  |  476.23867  | 464.88496 [50\%] |     1/4      |
|   3   |  454.50418  |  474.86977  | 459.59558 [25\%] |     1/4      |
|   4   |  453.80710  |  475.34262  | 455.96064 [10\%] |     1/4      |

The results of both cases show a subpar success rate regardless of threshold percentage. It can also be observed that the difference between resting and flexing standard deviation is very minimal, which may be why it was misclassifying the signals.

### References:
* https://royalsocietypublishing.org/doi/10.1098/rsta.2017.0254
* https://www.eurchembull.com/uploads/paper/6a9d85f5dbcc6a8a37b2fa3d8d2058f1.pdf
* https://math.stackexchange.com/questions/279980/difference-between-fourier-transform-and-wavelets
* https://www.mathworks.com/help/wavelet/gs/continuous-wavelet-transform-and-scale-based-analysis.html
* https://www.youtube.com/watch?v=qoMDpSatG7M
* [W2-5pm EMG](recordings/bicep_240221_142714.rhd)
* [Tr9-11am EMG](recordings/emg1_240222_091915.rhd)
* https://docs.python.org/3/library/multiprocessing.html
    * Note: There is a [bug](https://github.com/python/cpython/issues/94765) on new python versions with certain MacOS and Linux versions.
* https://wiki.python.org/moin/BitwiseOperators

### Notes:
Please do not use without permission.
