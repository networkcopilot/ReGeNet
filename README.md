# ReGeNet Framework Repository
Reflective-GeNet (ReGeNet), a multi-agent communication network copilot that incorporates a self- verification loop to reduce LLM-induced errors. ReGeNet extends [GeNet](https://github.com/networkcopilot/ICDCS25-GeNet), a multimodal copilot that interprets both textual and visual representations of network state to update configurations and topologies according to user intent.
ReGeNet's verification loop operates in a multi-agent manner, where one agent translates intent into actionable changes and another independently evaluates the outcome and provides corrective feedback. 


---

### Key Features

- **Reflective Multi-Agent Copilot**: ReGeNet is a multi-agent network copilot that extends GeNet with a self-verification loop to minimize LLM-induced errors in intent-based networking.

- **Advanced Topology Understanding**: Accurately converts diverse network topology images, from emulation outputs to low-quality hand-drawn sketches, into structured JSON representations using Vision-Language Large Models (VLLMs).

- **Reflective Intent Implementation**: Employs implementation and verification agents that iteratively refine configurations and topologies, enhancing reliability even for non-reasoning LLMs.

- **Comprehensive Benchmarking**: We evaluate 9 state-of-the-art LLMs for topology understanding and 2 top models for intent implementation, highlighting the role of reasoning ability, token efficiency, and verification loops.

- **Validated Performance**: We demonstrate improved intent implementation quality (compared to GeNet), robustness to input variability, and practical efficiency on a multimodal IBN benchmark inspired by realistic Cisco network scenarios.


### Motivation

Communication network engineering in enterprise environments is a complex and error-prone process, where configuration mistakes or overlooked topology changes can disrupt operations and introduce security risks. Traditional automation solutions mainly address device-level configuration and rely on textual input, leaving physical topology updates underexplored. Recent intent-based networking (IBN) approaches leverage large language models (LLMs) to simplify management, yet such models often produce erroneous or hallucinated outputs, highlighting the need for verification and feedback mechanisms. Existing verification techniques, however, focus primarily on formal configuration analysis and are less practical for holistic frameworks that must also process topology-level intents. ReGeNet was developed to bridge these gaps and advance the practical deployment of multimodal LLM-driven IBN.

### Core Modules
1. **Topology Understanding Module:**
   - Converts a network diagram into a structured JSON representation.
   - Supports diverse diagram formats and varying quality levels.
2. **Reflective Intent Implementation Module:**
   - Updates network configurations and topologies based on user-defined intents.
   - Provides explanations for every change to enhance user understanding.
   - Consists of n implementation agent and a verification agent iteratively refine topology and configuration updates until the intent is satisfied.
3. **Automatic LLM-Based Evaluation Framework:**
   - Automates the evaluation of implemented intents against predefined quality metrics.

### Use Cases
- **Network Expansion:** Add devices to a network with configurations automatically updated (e.g., adding PCs or servers to a topology).
- **Policy Updates:** Modify network configurations for tasks such as adding firewalls or changing access lists.
- **Visualization Enhancement:** Simplify the interpretation of complex or messy network diagrams.

---

## Dataset 
The [dataset](https://github.com/networkcopilot/ICDCS25-GeNet/tree/main/Dataset) is splitted into 2 main directory - **Topology based Scenarios** and **Configuration Based Scenarios**.

#### The Topology based scenarios:
- Adding Communication Servers (E)
- Adding DMZ (M)
- Adding DRA (H)
- Adding Local PCs (E)
- Internet Connectivity (M)

#### The Configuration base scenarios:
- Basic Zone Based Firewall (H)
- IP Traffic Export (M)
- Role Based CLI Access (E)
- Time Based Access List (E)
- Transparent IOS Firewall (M)

(scenarios divided into scenario types and complexity levels where (E) marks Easy, (M) marks Medium, and (H) marks Hard, based on expert survey)

### Dataset Directory Structure
Each directory consist of 3 folders:
1. **Initial Files** - The initial files consist a directory per scenario which consist of the input intent textual file and configuration textual file
2. **Scoring Keys** - The scoring keys for each scenario for measuring the level of success in implementing the intent
3. **Topology Image Variants** - The dataset for the Topology Understanding Module
4. **Topologies Ground Truth Representations** - The structured representations of the topologies per scenario which are used as a ground truth for the Topology Understanding part

The Topology Image Variants directory architecture:
 - Topology_image_variants
   - {visualization_format}
     - {diagram_type}
        - {scenario_name}
          - {scenario_name}.jpg (the diagram image)
          - GNS3 file or Powerpoint slide of the diagram (according to the visualization format)


Visualization_formats : [GNS3, Paper_Sketches, PowerPoint]

Diagram_type: [Messy_Layout, No_Labels_On_Edges, Normal]

---

## License

This project is licensed under [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en).
