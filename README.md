# SENTINEL
A suite of programs created to combat child sexual abuse media (CSAM) on the internet.

This is the current structure of the SENTINEL ecosystem, as of 13/1/2025:

**SENTINEL**: A Nous-Hermes based, Azure Cloud Services-powered, 280 million parameter MoRA specializing in developing anti-CSAM measures, analyst coordination, and target analysis. Closed source, controlled access.

**Core**: Serves as the primary execution hub, facilitating the launch of all associated scripts and enabling seamless interaction with the underlying database.

~~**Hasher**: Generates cryptographic hashes (MD5) of images to facilitate their unique identification and verification.~~

**Advanced Hashing Capabilities Environment (AHCE)**: Implements a variety of techniques, including procedural and geometric hashing, color histogram analysis, facial recognition, and a (WIP) deep learning model trained on CSAM. Hasher merged into AHCE on 13/1/2025.

~~**Hash Query**: Accepts a user-provided hash, cross-references it with the database of processed hashes, and notifies the user of any matching results, enabling further action by the user.~~

**Case Sync**: Enables collaboration between multiple instances of SENTINEL running on different machines, ensuring smooth data synchronization and sharing across systems.
