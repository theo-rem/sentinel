# SENTINEL
A suite of programs created to combat child sexual abuse media (CSAM) on the internet.

This is the current structure of the SENTINEL ecosystem, as of 4/4/2025:

**SENTINEL**: A Nous-Hermes based, Microsoft Azure-powered, 280 million parameter MoRA specializing in developing anti-CSAM measures, analyst coordination, and target analysis. Closed source, controlled access.

**MINUTEMAN**: Serves as the primary execution hub, facilitating the launch of all associated scripts and enabling seamless interaction with the underlying database.

**GOALKEEPER**: Implements a variety of techniques, including procedural and geometric hashing, color histogram analysis, facial recognition, and a (WIP) deep learning model trained on CSAM. 

**ALTEREGO**: Enables collaboration between multiple instances of SENTINEL running on different machines, ensuring smooth data synchronization and sharing across systems.

## How it works
### SENTINEL
**SENTINEL** was trained on publicly available information, including (but not limited to) documents relating to the procedures and algorithms used in CSAM identification, court documents detailing the persecution of CSAM production and distribution (primarily within the United States), as well as studies and statistics from NCMEC, IWF, Thorn Research et cetera. 

Inference and training was conducted on 8x A100-powered compute platforms and completed after 122 hours (horribly slow and expensive, but necessary).
SENTINEL also has access to the real-time Internet as part of its web crawler mechanism (WIP).

Through inspection of SENTINEL's thought logic, we noticed its initiative to develop, improve and deploy GOALKEEPER autonomously. However, since SENTINEL does not specialize in any of the programming languages GOALKEEPER is written in, this behavior is currently discouraged. The reason for this is that, as of right now, many of the features we seek to implement cannot function in a stable enough manner so as to make it viable for production code. 

SENTINEL's model, MoRA and memories are stored on Azure Storage Accounts and currently occupy 780GB of storage space.

SENTINEL's current uses are:

- Analyst consultations

- Development assistance

- Platform investigation

- Open-source intelligence analysis against individuals and/or groups connected with CSAM production/distribution.

The system is, at least for now, managed by a team of three, with two of the members having a support role in the further refinement of SENTINEL's MoRA. Access is limited to a maximum of five users: 3 operators and 2 analysts. 
Access to SENTINEL is strictly regulated with biometric authentication of all users. 

SENTINEL is powered by the following Azure services:

- 3x E16-8s v3 virtual machines

- Azure AI Services

- Azure Functions

- Azure Managed Disks for persistent storage.

- Azure Storage Accounts for SENTINEL MoRA applications.

### MINUTEMAN
In development.

### GOALKEEPER
In its first iteration, GOALKEEPER was no more than an image similarity detection algorithm of some 3 components with no database, a single operator, and devastatingly low accuracy. Today, GOALKEEPER combines 8 commercially available and 2 in-house algorithms in the hunt for CSAM. In order to deploy newer iterations of GOALKEEPER in the field, a starting dataset was necessary. As of 1/4/2025, GOALKEEPER is working with a dataset of ~450,000 individual cases.

GOALKEEPER implements several image similarity detection algorithms.

- **BAPTISTE** (Fourier Transform): BAPTISTE transforms an image into its constituent frequencies, enabling the detection of patterns and features that might not be visible to the human eye. By analyzing these frequencies, GOALKEEPER can identify similarities and differences between images more effectively.


- **WAYLAND** (Histogram of Oriented Gradients): WAYLAND extracts features from an image by calculating the distribution of gradients in localized portions of the image. This allows GOALKEEPER to create a unique representation of the image's content, which can be used for comparison and matching purposes.


- **CHALET** (Color Histogram Analysis): CHALET generates a histogram of the color distribution within an image. By comparing color histograms, GOALKEEPER can determine the similarity between images and identify potential matches, even if the images have been altered or manipulated.


- **HILDRETH** (Perceptual Hashing): HILDRETH generates a compact representation of an image's content, allowing for efficient comparison and matching. This algorithm is particularly useful for detecting similar images, even when they have been modified or subjected to various transformations.


- **BOVIK** (Structural Similarity Index): BOVIK measures the structural similarity between two images by comparing their luminance, contrast, and structure. This provides a quantitative measure of image similarity, which GOALKEEPER employs to identify matching or near-matching images.
  

- **VINYALS** (Multi-Modal Embedding): VINYALS creates a unified representation of different types of data, such as images, text, and audio. By embedding this data into a single space, GOALKEEPER can more effectively compare and analyze multimodal content.

- **STRONGLOWE** (Scale-Invariant Feature Transform): STRONGLOWE identifies key features within an image that are invariant to scale and rotation. By extracting these features, GOALKEEPER can match images across various transformations in object geometry.

- **PENTLAND** (Facial Recognition): PENTLAND creates a facial signature and stores the datapoints it collects as hashes, which are then transfered to a seperate DB to be ready to deploy if PENTLAND is invoked by an analyst. PENTLAND is highly susceptible to inaccuracy when deployed on low-quality media, and is reserved for high-definition content with potentially actionable intelligence within.

GOALKEEPER employs scale normalization and weighting techniques to ensure that the algorithms' outputs are comparable and can be effectively combined for accurate detection and identification of target media.


Scale normalization is the process of transforming the output of each algorithm to a common scale, typically between 0 and 1 (although this goes above 100 for certain algorithms). This allows for a fair comparison between the different algorithms, as their outputs are now on the same scale. For example, if one algorithm produces a similarity score between 0 and 100, while another produces a score between 0 and 1, scale normalization would transform both scores to a common range, such as 0 to 1.

Weighting, on the other hand, is the process of assigning different levels of importance to each algorithm's output. This is necessary because some algorithms may be more accurate or relevant for detecting specific types of CSAM. By assigning weights to each algorithm, GOALKEEPER can prioritize the more accurate or relevant algorithms when assisting the analysts with decision-making. 

For example, if STRONGLOWE is found to be more accurate at detecting manipulated images, it may be assigned a higher weight than other algorithms. Conversely, if CHALET is less effective for a particular type of media, it may be assigned a lower weight. In newer iterations of GOALKEEPER, operators and analysts are able to assign weights from 0 to 1 according to their needs and use cases.

GOALKEEPER compensates for the varying accuracies and grading scales of its constituent algorithms by employing scale normalization and weighting techniques. This ensures that the system can effectively combine the outputs of the different algorithms to make accurate decisions about the presence of CSAM. 

The results of GOALKEEPER analyses are graded according to their final weighed score, which is then sorted into several categories. The categories are as follows:

- **90 - 100** - **Definitive Association (X)**

Images are functionally identical—any variation is imperceptible or purely metadata-based. Treat as confirmed duplication.

- **75** - **89**	- **Critical Association (A)**

High-confidence match with minor modifications. Likely altered for obfuscation or compression. Requires immediate investigative review.

- **50** - **74** -	**Substantial Association (P)**

Core structural elements remain intact despite visible modifications. Possible deliberate manipulation. Further analysis required.

- **0** - **49** -	**Negligible Association (L)**

Minimal detectable commonalities. Potentially coincidental resemblance. Low priority for further examination.


### ALTEREGO
In development.
