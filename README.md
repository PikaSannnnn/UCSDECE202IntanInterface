# Tiles Game Demo Intan Interface
This is the Intan Interface for the white tiles demo for ECE202 Group 7. The purpose of this interface is to connect to the Intan software, read the EMG data frome **TWO** channels and convert to game controls, i.e. left arm = move left, right arm = move right.  

### Task List:
* [x] Read from Intan
* [ ] Calibration
    * Determine resting potential range
    * Determine threshold for "flexing" potential minimum
* [ ] Read from 2 channels
* [ ] Link to game movements

### Sample Waveforms:
<div style="display: flex;">
    <img src="image.png">
Figure 1: Resting Waveform
![Resting Sample](image.png)!

Figure 2: Flexing Waveform
![Flexing Sample](image-2.png)
</div>

### Calibration:
#### Iteration 2 CWT Frequency-Time Power Mean Analysis:
The Spectrogram used for Lab 5 would not work for python when I tried implementing it. After a couple of hours of researching, I found a useful method: **cwt**, from the `PyWavelets` library. Countinuous Wavelet Transform (CWT) is used  because we would like to classify flexing depending on the frequency of high power signals. If we refer back to Figure 2, we can observe higher peaks compared to Figure 1 for resting. This decision was made after the inconsistency and inaccuracy of iteration 1, which was primarily caused by the presence of low potential points in the waveform in both states. 

Our objective is to effectively measure the frequency of high power signals per time period and classify it as flexing or resting based whether it passes a threshold. After some research, it is found that CWT has high performance results and is effective for our objective in detecting the presence of high power signals at higher frequencies. I used this to help understand and implement the CWT components: https://www.youtube.com/watch?v=qoMDpSatG7M. All references for research are provided in the [references](#references).

**Choosing the correct wavelet:**
A graph of each different wavelets are provided. The same recording data and timestamps were used for each with 60% resting and 40% flexing. The recording used was pre-captured and is the same as the EMG recording used for Lab 5 W2-5pm, provided in the reference.
<details>
    <summary>Wavelets (Click to View Plots)</summary>
    <ul>
        <il><img src="wavelets\Screenshot 2024-03-09 221132.png" alt="cgau1"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221140.png" alt="cgau2"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221155.png" alt="cgau4"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221201.png" alt="cgau5"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221209.png" alt="cgau6"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221231.png" alt="cmor"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221240.png" alt="fbsp"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221249.png" alt="gaus1"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221303.png" alt="gaus2"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221329.png" alt="mexh"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221337.png" alt="morl"></li>
        <il><img src="wavelets\Screenshot 2024-03-09 221347.png" alt="shannon"></li>
    </ul>
</details>
Based on these plots, `mexh` waveform provides the clearest distinction betwen resting and flexing. This will be used to model all calibration and measuring.

#### Iteration 1 Standard Deviation:
**Notes**: Not reliable due to regular lower potentials in the waveform. Notice in both sets of trials, the standard deviation of thee flexing remained relatively close to the resting. This means at higher sample rates, the standard deviation is more likely to be incorrectly classified. This can be shown with association such that in these trial sets, the sample time was 5 seconds (the same as the calibration time), yet it still could not achieve 100% accuracy when needed. This same situation occurs with mean as it is related.

Calibration detects the standard deviation of potential of both resting and flexing. A lower threshold of which the standard deviation must exceed to be considered "flexing" is computed as a percentage between the two state's standard deviation. Two version of standard deviation were calculated, tested, and compared under three trials of the same sample EMG recording:
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

Why standard deviation? If we look at the following EMG recording plot for resting state:  
![Resting Sample](image.png)!
We observe regular and smaller potential variance such that a pattern can be recognized. However, if we look at the EMG recording plot for flexing state:  
![alt text](image-2.png)
We can observe a more chaotic variance in the potentials such that we cannot observe a regular pattern. It becomes clear that the standard deviation is higher for the flexing state.


### References:
* https://royalsocietypublishing.org/doi/10.1098/rsta.2017.0254
* https://www.eurchembull.com/uploads/paper/6a9d85f5dbcc6a8a37b2fa3d8d2058f1.pdf
* https://math.stackexchange.com/questions/279980/difference-between-fourier-transform-and-wavelets
* https://www.youtube.com/watch?v=qoMDpSatG7M
* [W2-5pm Omar's EMG](c:/Users/Pika-Sannnnn/Downloads/emg_lab_omar_bicep_240221_142714.rhd)

### Notes:
Recorded data is in microV for potential over seconds

Please do not use without permission.  
\- Stephen Dong
