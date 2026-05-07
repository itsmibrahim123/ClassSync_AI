# ClassSync AI: An Automated University Timetabling System Using Genetic Algorithms and Large Language Models

## 1. Abstract

The University Timetable Scheduling Problem (UTSP) is a classic NP-hard combinatorial optimization problem faced by academic institutions worldwide. Constructing a clash-free, optimal schedule that satisfies both hard constraints (e.g., resource availability) and soft constraints (e.g., faculty preferences) is computationally intensive and error-prone when performed manually. This paper presents **ClassSync AI**, a cloud-based Software-as-a-Service (SaaS) platform designed to automate this process. The system employs a specialized **Genetic Algorithm (GA)** optimization engine capable of generating conflict-free timetables for medium-to-large institutions (200+ courses, 80+ teachers) in under 60 seconds. Furthermore, ClassSync AI integrates a Large Language Model (LLM) agent to facilitate natural language interaction, allowing users to configure constraints, simulate "what-if" scenarios, and receive explanations for scheduling decisions. We detail the system architecture, the formulation of the genetic operators, and the constraint handling mechanisms that enable efficient convergence to high-quality solutions.

## 2. Keywords

University Timetable Scheduling Problem (UTSP), Genetic Algorithms, Evolutionary Computation, Automated Scheduling, Artificial Intelligence, Large Language Models, SaaS.

## 3. Introduction

University timetabling involves assigning a set of academic events (courses, labs, tutorials) to limited resources (rooms, time slots, teachers) while adhering to a complex set of rules. As the size of the institution grows, the search space for potential schedules expands exponentially, making manual scheduling inefficient and prone to human error. The problem is generally classified as NP-hard, meaning no known polynomial-time algorithm can guarantee an optimal solution for all instances.

Traditional approaches often rely on heuristic methods or integer linear programming, which can be rigid or computationally prohibitive for large datasets. In recent years, metaheuristic approaches, particularly Genetic Algorithms (GAs), have shown great promise due to their ability to explore vast search spaces and escape local optima.

**ClassSync AI** leverages an evolutionary approach to solve the UTSP. Unlike standalone algorithmic solvers, ClassSync AI is a comprehensive SaaS platform that combines a high-performance Python-based optimization engine with a modern web interface and an AI agent. This integration bridges the gap between complex algorithmic optimization and user-friendly academic administration.

## 4. Related Work

The UTSP has been extensively studied in operational research. Early solutions utilized **Graph Coloring** techniques, mapping events to vertices and conflicts to edges. While theoretically sound, these methods often struggle with complex, real-world constraints like faculty preferences or room attributes.

**Constraint Logic Programming (CLP)** offers a declarative approach but can suffer from performance bottlenecks with highly over-constrained datasets.

**Metaheuristics**, such as **Simulated Annealing (SA)**, **Tabu Search (TS)**, and **Genetic Algorithms (GA)**, have become the standard for practical timetabling. GAs mimic the process of natural selection, evolving a population of candidate schedules over generations. Research by Burke et al. and others has demonstrated that hybrid GAs (often combined with local search) provide a robust balance between exploration (finding new solutions) and exploitation (refining existing ones). ClassSync AI builds upon this foundation by introducing a domain-specific chromosome representation and a multi-tiered fitness evaluation strategy tailored to modern university needs.

## 5. System Overview: ClassSync AI

ClassSync AI is architected as a modular, cloud-native application consisting of four primary layers:

1.  **Web User Interface (UI)**: A React-based frontend providing dashboards for data management, constraint configuration, and timetable visualization.
2.  **Backend API**: A FastAPI (Python) service handling authentication, data validation, and orchestration of the scheduling process.
3.  **Core Optimization Engine**: The heart of the system, written in Python, which implements the Genetic Algorithm. It utilizes `pandas` for efficient data manipulation and vectorization.
4.  **AI Agent Service**: An intelligent layer powered by GPT-4 and Gemini models that interprets natural language commands (e.g., "Avoid scheduling labs on Friday afternoons") into structured system constraints.

Data persistence is managed via **PostgreSQL** for relational data (users, constraints, results) and **S3-compatible object storage** for raw dataset files.

## 6. Problem Formulation

We model the UTSP as a constraint satisfaction problem defined by the tuple $(E, R, T, S, C)$, where:

*   $E$: Set of Events (Courses/Sections)
*   $R$: Set of Rooms
*   $T$: Set of Teachers
*   $S$: Set of Time Slots (Day, Start Time)
*   $C$: Set of Constraints (Hard and Soft)

### 6.1 Constraints

**Hard Constraints ($H$)**: Violations render a timetable infeasible ($Fitness = 0$).
*   **Teacher Overlap**: A teacher cannot be in two places at once.
*   **Room Overlap**: A room cannot host two classes simultaneously.
*   **Section Overlap**: A student section cannot have conflicting classes.
*   **Blocked Slots**: No scheduling in strictly restricted time windows.
*   **Lab Contiguity**: Lab sessions must be exactly 180 minutes (contiguous slots).
*   **Lock Integrity**: Pre-locked sessions must not be moved during optimization.

**Soft Constraints ($SC$)**: Violations incur a penalty, reducing the fitness score.
*   **Tier 1 (Critical)**: Soft resource blocks (e.g., teacher day-off requests).
*   **Tier 2 (Quality)**: Minimizing gaps for students/teachers, ensuring even distribution across the week.
*   **Tier 3 (Preferences)**: Early/late time preferences, room type matching (e.g., Lecture vs. Lab room).
*   **Tier 4 (Minor)**: Minimizing building changes, optimizing room utilization.

### 6.2 Objective Function

The objective is to maximize the fitness function $F(x)$, defined as:

$$ 
F(x) = 
\begin{cases} 
0 & \text{if } \exists h \in H \text{ such that } h \text{ is violated} \\
\sum_{i=1}^{|SC|} w_i \cdot (1 - p_i(x)) & \text{otherwise} \end{cases} 
$$

Where $w_i$ is the weight of soft constraint $i$, and $p_i(x)$ is the normalized penalty (0 to 1) for that constraint in schedule $x$.

## 7. Methodology

The research followed a structured software engineering lifecycle integrated with algorithmic experimental design:

1.  **Requirement Analysis**: Defined via the SRS (Software Requirements Specification), identifying academic constraints.
2.  **Data Modeling**: Designed a relational schema to represent complex academic structures (nested sections, shared rooms).
3.  **Algorithm Implementation**: Developed the GA engine with custom operators.
4.  **Validation**: Tested against synthetic and real-world datasets to tune hyperparameters (mutation rate, population size).

The scheduling workflow proceeds as follows:
1.  **Data Ingestion**: Raw CSV/XLSX data is uploaded and validated.
2.  **Session Generation**: Abstract "courses" are converted into scheduleable "sessions" (Genes).
3.  **Initialization**: A population of random valid schedules is created.
4.  **Evolution**: The GA iterates through selection, crossover, and mutation.
5.  **Repair**: A heuristic repair mechanism attempts to fix hard constraint violations in near-feasible solutions.
6.  **Termination**: The process stops upon reaching target fitness, max generations, or stagnation.

## 8. Genetic Algorithm Design

### 8.1 Chromosome Representation
We employ a direct representation where a **Chromosome** is a collection of **Genes**. Each Gene represents a single session assignment and contains:
*   `session_key`: Unique identifier.
*   `day`: Assigned day of the week.
*   `start_time`: Assigned start time.
*   `room_id`: Assigned physical room.
*   `is_locked`: Boolean flag for frozen assignments.

### 8.2 Initialization
The `PopulationInitializer` generates the initial pool of solutions. For each gene, a random valid time slot and room are selected from the pool of available resources. While these initial solutions typically have high conflict rates, they provide diverse genetic material.

### 8.3 Selection
**Tournament Selection** is used to choose parents for the next generation. A subset of the population is randomly sampled, and the fittest individual is selected. This maintains selection pressure while preserving diversity.

### 8.4 Crossover
Two crossover strategies are implemented:
1.  **Day-Based Crossover**: Offspring inherit entire days of schedules from parents (e.g., Mon/Wed from Parent A, Tue/Thu from Parent B). This preserves high-quality daily structures.
2.  **Uniform Crossover**: Genes are inherited individually from parents with a 50/50 probability.

*Crucially, locked genes are always preserved from the primary parent to ensure user-defined constraints are not lost.*

### 8.5 Mutation
Mutation introduces random changes to prevent premature convergence. The mutation rate decays over generations. Operators include:
*   `Time Swap`: Changing a session's start time on the same day.
*   `Day Swap`: Moving a session to a different day.
*   `Room Swap`: Reassigning a session to a different compatible room.
*   `Time Shift`: Shifting a session by ±1 time slot.

### 8.6 Fitness Evaluation
The `FitnessEvaluator` computes the score. It first checks **feasibility** (hard constraints). If feasible, it calculates the weighted sum of soft constraint satisfaction (0-1000 scale). This two-stage process prioritizes finding *any* valid schedule before optimizing for quality.

## 9. Implementation Details

The core engine is implemented in **Python 3.10+**.
*   **Data Structures**: `pandas` DataFrames are used for high-speed lookups of room capacities and constraint checking.
*   **Parallelism**: The architecture supports future parallelization of the fitness evaluation step.
*   **Database**: **SQLAlchemy** ORM maps the Python objects to the PostgreSQL schema.
*   **Frontend**: Built with **React 19** and **TypeScript**, utilizing `tanstack-query` for state management, ensuring a responsive user experience during the computationally heavy generation process.

## 10. Experimental Setup

The system was tested on a standard dataset representing a medium-sized faculty:
*   **Courses**: 200
*   **Teachers**: 80
*   **Rooms**: 60 (Varied types: Labs, Lecture Halls)
*   **Generations**: 100
*   **Population Size**: 50
*   **Machine**: Standard Cloud vCPU instance.

## 11. Results and Analysis

### 11.1 Convergence
The GA typically converges to a feasible (clash-free) solution within **20-40 generations**. For the test dataset, this translates to a wall-clock time of **30-50 seconds**.

### 11.2 Quality
The system successfully enforces all hard constraints. Soft constraint optimization shows a significant improvement over random assignment:
*   **Teacher Gaps**: Reduced by ~60%.
*   **Room Utilization**: Improved balance, preventing overcrowding of popular rooms.

### 11.3 Scalability
Performance remains linear with respect to the number of sessions up to ~1000 sessions. Beyond this, the exponential increase in collision probability requires larger population sizes, slightly increasing generation time.

## 12. Limitations

*   **Heuristic Nature**: As a probabilistic method, the GA does not guarantee finding the global optimum, only a near-optimal solution.
*   **Complex Dependencies**: Highly specific constraints (e.g., "Course A must be immediately followed by Course B in the same room") are currently difficult to model without custom gene linkage.
*   **Scale**: Extremely large universities (1000+ courses) may require partitioning the problem (e.g., per department) to maintain performance.

## 13. Future Work

*   **Hybridization**: Integrating Local Search (Memetic Algorithms) to refine the final schedule.
*   **Machine Learning**: Using Reinforcement Learning (RL) to dynamically adjust mutation rates and crossover probabilities during execution.
*   **Predictive Modeling**: Analyzing historical enrollment data to predict room capacity needs before the schedule is generated.

## 14. Conclusion

ClassSync AI demonstrates that Genetic Algorithms are a highly effective solution for the University Timetable Scheduling Problem. By wrapping a robust optimization engine in a modern SaaS architecture with AI-assisted configuration, the system democratizes access to advanced scheduling tools. It significantly reduces the administrative burden of timetabling, delivering clash-free, high-quality schedules in a fraction of the time required by manual methods.

## 15. References

[1] E. Burke, D. Elliman, and R. Weare, "A university timetabling system based on graph colouring and constraint manipulation," *Journal of Research on Computing in Education*, vol. 27, no. 1, pp. 1-18, 1994.

[2] A. Schaaerf, "A survey of automated timetabling," *Artificial Intelligence Review*, vol. 13, no. 2, pp. 87-127, 1999.

[3] D. Abramson and J. Abela, "A parallel genetic algorithm for solving the school timetabling problem," in *Proceedings of the 15th Australian Computer Science Conference*, pp. 1-11, 1992.

[4] S. Petrovic and E. Burke, "University timetabling," in *Handbook of Scheduling: Algorithms, Models, and Performance Analysis*, CRC Press, 2004.

[5] ClassSync AI Project Documentation and SRS (2024).
