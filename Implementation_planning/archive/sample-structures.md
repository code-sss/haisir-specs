# hAIsir — Sample Content Structures
> Covers structured (board) and open (tutor) tracks with concrete table-level examples.
> See `Implementation_planning/rag-and-curriculum-decisions.md` for design decisions behind these structures.

---

## Core Hierarchy

```
categories
  └── course_path_nodes  (self-referential tree, arbitrary depth)
        └── topics        (hang off LEAF course_path_node only)
              └── topic_contents  (1 per type: video | pdf | text)
                    └── topic_content_chunks  (RAG: chunks of pdf/text items)
```

**Key rules:**
- Topics attach only to **leaf** `course_path_nodes` (nodes with no children)
- Each topic has at most **1 content item per type** (1 video + 1 pdf + 1 text)
- `node_type` is a free string — reserved: `grade`, `subject`; defaults: `course`, `chapter`, `module`, `section`, `unit`, `week`

---

## STRUCTURED TRACK — NCERT Class 6 Science

### `categories`

| id | name | path_type |
|---|---|---|
| `cat-ncert` | NCERT | structured |

---

### `course_path_nodes` — platform-owned

| id | parent_id | name | node_type | order | owner_type | owner_id |
|---|---|---|---|---|---|---|
| `cpn-g6` | NULL | Grade 6 | grade | 6 | platform | NULL |
| `cpn-g6-sci` | `cpn-g6` | Science | subject | 1 | platform | NULL |
| `cpn-g6-sci-ch01` | `cpn-g6-sci` | Food: Where Does It Come From? | chapter | 1 | platform | NULL |
| `cpn-g6-sci-ch02` | `cpn-g6-sci` | Components of Food | chapter | 2 | platform | NULL |
| `cpn-g6-sci-ch03` | `cpn-g6-sci` | Fibre to Fabric | chapter | 3 | platform | NULL |
| `cpn-g6-sci-ch04` | `cpn-g6-sci` | Sorting Materials into Groups | chapter | 4 | platform | NULL |
| `cpn-g6-sci-ch05` | `cpn-g6-sci` | Separation of Substances | chapter | 5 | platform | NULL |
| `cpn-g6-sci-ch06` | `cpn-g6-sci` | Changes Around Us | chapter | 6 | platform | NULL |
| `cpn-g6-sci-ch07` | `cpn-g6-sci` | Getting to Know Plants | chapter | 7 | platform | NULL |
| `cpn-g6-sci-ch08` | `cpn-g6-sci` | Body Movements | chapter | 8 | platform | NULL |
| `cpn-g6-sci-ch09` | `cpn-g6-sci` | Living Organisms — Characteristics and Habitats | chapter | 9 | platform | NULL |
| `cpn-g6-sci-ch10` | `cpn-g6-sci` | Motion and Measurement of Distances | chapter | 10 | platform | NULL |
| `cpn-g6-sci-ch11` | `cpn-g6-sci` | Light, Shadows and Reflections | chapter | 11 | platform | NULL |
| `cpn-g6-sci-ch12` | `cpn-g6-sci` | Electricity and Circuits | chapter | 12 | platform | NULL |
| `cpn-g6-sci-ch13` | `cpn-g6-sci` | Fun with Magnets | chapter | 13 | platform | NULL |
| `cpn-g6-sci-ch14` | `cpn-g6-sci` | Water | chapter | 14 | platform | NULL |
| `cpn-g6-sci-ch15` | `cpn-g6-sci` | Air Around Us | chapter | 15 | platform | NULL |
| `cpn-g6-sci-ch16` | `cpn-g6-sci` | Garbage In, Garbage Out | chapter | 16 | platform | NULL |

> Tree shape: `grade → subject → chapter`. Chapters are the leaf nodes — topics attach here.

---

### `topics` — sections within each chapter (platform-owned)

#### Chapter 1 — Food: Where Does It Come From?
| id | course_path_node_id | title | order | status | owner_type |
|---|---|---|---|---|---|
| `t-ch01-01` | `cpn-g6-sci-ch01` | Food Variety | 1 | live | platform |
| `t-ch01-02` | `cpn-g6-sci-ch01` | Food Materials and Sources | 2 | live | platform |
| `t-ch01-03` | `cpn-g6-sci-ch01` | Plant Parts We Eat | 3 | live | platform |
| `t-ch01-04` | `cpn-g6-sci-ch01` | Animal Products as Food | 4 | live | platform |
| `t-ch01-05` | `cpn-g6-sci-ch01` | What Do Animals Eat? | 5 | live | platform |

#### Chapter 2 — Components of Food
| id | course_path_node_id | title | order | status | owner_type |
|---|---|---|---|---|---|
| `t-ch02-01` | `cpn-g6-sci-ch02` | What Do Different Foods Contain? | 1 | live | platform |
| `t-ch02-02` | `cpn-g6-sci-ch02` | What Nutrients Do for Our Body | 2 | live | platform |
| `t-ch02-03` | `cpn-g6-sci-ch02` | Balanced Diet | 3 | live | platform |
| `t-ch02-04` | `cpn-g6-sci-ch02` | Deficiency Diseases | 4 | live | platform |

#### Summary — all chapters
| Chapter | Topics |
|---|---|
| Ch 01 — Food: Where Does It Come From? | Food Variety · Food Materials and Sources · Plant Parts We Eat · Animal Products as Food · What Do Animals Eat? |
| Ch 02 — Components of Food | What Do Different Foods Contain? · What Nutrients Do for Our Body · Balanced Diet · Deficiency Diseases |
| Ch 03 — Fibre to Fabric | Variety in Fabrics · Types of Fibres · Plant Fibres: Cotton and Jute · Spinning Cotton Yarn · Yarn to Fabric |
| Ch 04 — Sorting Materials into Groups | Objects Around Us · Appearance and Texture · Solubility and Transparency · Sink or Float |
| Ch 05 — Separation of Substances | Why Separate Substances? · Handpicking/Threshing/Winnowing · Sieving and Sedimentation · Filtration and Evaporation · Saturated Solutions |
| Ch 06 — Changes Around Us | Reversible Changes · Irreversible Changes · Expansion and Contraction |
| Ch 07 — Getting to Know Plants | Herbs Shrubs and Trees · Stem and Its Functions · Leaf: Veins/Transpiration/Photosynthesis · Root Types and Functions · Flower Parts and Reproduction |
| Ch 08 — Body Movements | Bones Joints and Movement · Ball-Socket/Hinge/Pivot Joints · Gait of Animals · Earthworm and Cockroach Movement |
| Ch 09 — Living Organisms | Habitat and Adaptation · Aquatic and Terrestrial Habitats · Aerial and Desert Habitats · Characteristics of Living Organisms |
| Ch 10 — Motion and Measurement | Need for Measurement and Standard Units · Measuring Length Correctly · Measuring Curved Lines · Types of Motion |
| Ch 11 — Light Shadows Reflections | Transparent/Opaque/Translucent · How Shadows Form · Pinhole Camera · Mirrors and Reflections |
| Ch 12 — Electricity and Circuits | Electric Cell and Bulb · Electric Circuit and Switch · Conductors and Insulators |
| Ch 13 — Fun with Magnets | Magnetic/Non-magnetic Materials · Poles of a Magnet · Finding Direction · Attraction and Repulsion · Making a Magnet |
| Ch 14 — Water | Sources of Water · The Water Cycle · Floods and Droughts · Water Conservation |
| Ch 15 — Air Around Us | Air is Present Everywhere · Composition of Air · Oxygen in Water and Soil · Role of Atmosphere |
| Ch 16 — Garbage In Garbage Out | Dealing with Garbage · Vermicomposting · Recycling Paper and Plastic · Plastics: Boon or Curse? |

---

### `topic_contents` — Chapter 1, Topic 1 (1 per type)

| id | topic_id | content_type | title | url / path | order | extraction_status |
|---|---|---|---|---|---|---|
| `tc-ch01-01-pdf` | `t-ch01-01` | pdf | NCERT Ch1 Sec1 — Food Variety | /data/pdfs/g6sci-ch01-sec1.pdf | 1 | complete |
| `tc-ch01-01-vid` | `t-ch01-01` | video | Food Varieties Around India | https://youtube.com/... | 2 | skipped |
| `tc-ch01-01-txt` | `t-ch01-01` | text | Summary Note | "All food comes from plants or animals..." | 3 | complete |

---

### `topic_content_chunks` — for `tc-ch01-01-pdf`

600-char pieces, 100-char overlap. Videos are skipped.

| id | topic_id | topic_content_id | chunk_index | content (excerpt) | embedding |
|---|---|---|---|---|---|
| `ck-ch01-01-0` | `t-ch01-01` | `tc-ch01-01-pdf` | 0 | "Food is one of our basic needs. We eat a variety of food items every day. Rice, roti, vegetables, fruits, milk, eggs and meat are some of the food items that people eat..." | `[0.12, 0.08, ...]` |
| `ck-ch01-01-1` | `t-ch01-01` | `tc-ch01-01-pdf` | 1 | "...different people eat different kinds of food. People living in coastal areas eat a lot of fish. In northern India, wheat is commonly eaten while in southern India rice is the staple food..." | `[0.09, 0.14, ...]` |
| `ck-ch01-01-2` | `t-ch01-01` | `tc-ch01-01-pdf` | 2 | "All the food we eat comes from plants and animals. Farmers grow crops like wheat, rice, vegetables and fruits. Animals like cows, hens and goats give us milk, eggs and meat." | `[0.21, 0.06, ...]` |

---

### Institutional copy — St. Mary's School adopts NCERT

When St. Mary's imports the NCERT board, the platform `course_path_nodes` and `topics` are cloned as institution-owned rows.

#### `organizations`
| id | name | primary_board_category_id |
|---|---|---|
| `org-stmarys` | St. Mary's School, Mumbai | `cat-ncert` |

#### `board_adoptions`
| id | organization_id | category_id | status |
|---|---|---|---|
| `ba-stmarys-ncert` | `org-stmarys` | `cat-ncert` | active |

#### `course_path_nodes` — institution copies (cloned from platform)
| id | parent_id | name | node_type | owner_type | owner_id |
|---|---|---|---|---|---|
| `cpn-sm-g6` | NULL | Grade 6 | grade | institution | `org-stmarys` |
| `cpn-sm-g6-sci` | `cpn-sm-g6` | Science | subject | institution | `org-stmarys` |
| `cpn-sm-ch01` | `cpn-sm-g6-sci` | Food: Where Does It Come From? | chapter | institution | `org-stmarys` |
| ... | ... | ... | ... | institution | `org-stmarys` |

St. Mary's can add institution-specific content (e.g. a supplemental topic) without touching the platform copy:

| id | course_path_node_id | title | order | status | owner_type | owner_id |
|---|---|---|---|---|---|---|
| `t-sm-ch01-extra` | `cpn-sm-ch01` | Local Food Practices (Mumbai) | 6 | live | institution | `org-stmarys` |

---

## OPEN TRACK — Tutor-Built Courses

Node types are tutor's choice. Topics always hang off the leaf node regardless of depth.

---

### Example 1 — DeepLearning.AI RAG Course (modular, 2-level)

```
CoursePathNode (course):  "Retrieval Augmented Generation"
  └── CoursePathNode (module): "Module 1 — RAG Overview"             ← leaf node
        └── Topic: "Introduction to RAG"
        └── Topic: "Applications of RAG"
        └── Topic: "RAG Architecture Overview"
        └── Topic: "Introduction to LLMs"
        └── Topic: "LLM Calls and Crafting Simple Augmented Prompts"
        └── Topic: "Introduction to Information Retrieval"
  └── CoursePathNode (module): "Module 2 — Information Retrieval and Search Foundations"
        └── Topic: "Retriever Architecture Overview"
        └── Topic: "Metadata Filtering"
        └── Topic: "Keyword Search — TF-IDF"
        └── Topic: "Keyword Search — BM25"
        └── Topic: "Semantic Search — Introduction"
        └── Topic: "Semantic Search — Embedding Model Deep Dive"
        └── Topic: "Vector Embeddings in RAG"
        └── Topic: "Hybrid Search"
        └── Topic: "Evaluating Retrieval"
        └── Topic: "Retrieval Metrics"
  └── CoursePathNode (module): "Module 3 — Information Retrieval with Vector Databases"
        └── Topic: "Approximate Nearest Neighbors (ANN)"
        └── Topic: "Vector Databases"
        └── Topic: "Introduction to the Weaviate API"
        └── Topic: "Chunking"
        └── Topic: "Advanced Chunking Techniques"
        └── Topic: "Query Parsing"
        └── Topic: "Cross-encoders and ColBERT"
        └── Topic: "Reranking"
  └── CoursePathNode (module): "Module 4 — LLMs and Text Generation"
        └── Topic: "Transformer Architecture"
        └── Topic: "LLM Sampling Strategies"
        └── Topic: "Prompt Engineering — Basics"
        └── Topic: "Prompt Engineering — Advanced Techniques"
        └── Topic: "Handling Hallucinations"
        └── Topic: "Agentic RAG"
        └── Topic: "RAG vs Fine-Tuning"
  └── CoursePathNode (module): "Module 5 — RAG Systems in Production"
        └── Topic: "What Makes Production Challenging"
        └── Topic: "Implementing RAG Evaluation Strategies"
        └── Topic: "Logging, Monitoring and Observability"
        └── Topic: "Quantization"
        └── Topic: "Security"
        └── Topic: "Multimodal RAG"
```

#### `course_path_nodes`
| id | parent_id | name | node_type | order | owner_type | owner_id |
|---|---|---|---|---|---|---|
| `cpn-rag` | NULL | Retrieval Augmented Generation | course | 1 | tutor | `zain_sub` |
| `cpn-rag-m1` | `cpn-rag` | Module 1 — RAG Overview | module | 1 | tutor | `zain_sub` |
| `cpn-rag-m2` | `cpn-rag` | Module 2 — Information Retrieval and Search Foundations | module | 2 | tutor | `zain_sub` |
| `cpn-rag-m3` | `cpn-rag` | Module 3 — Information Retrieval with Vector Databases | module | 3 | tutor | `zain_sub` |
| `cpn-rag-m4` | `cpn-rag` | Module 4 — LLMs and Text Generation | module | 4 | tutor | `zain_sub` |
| `cpn-rag-m5` | `cpn-rag` | Module 5 — RAG Systems in Production | module | 5 | tutor | `zain_sub` |

#### `topics` — Module 2 expanded
| id | course_path_node_id | title | order | status | owner_type |
|---|---|---|---|---|---|
| `t-rag-m2-01` | `cpn-rag-m2` | Retriever Architecture Overview | 1 | live | tutor |
| `t-rag-m2-02` | `cpn-rag-m2` | Metadata Filtering | 2 | live | tutor |
| `t-rag-m2-03` | `cpn-rag-m2` | Keyword Search — TF-IDF | 3 | live | tutor |
| `t-rag-m2-04` | `cpn-rag-m2` | Keyword Search — BM25 | 4 | live | tutor |
| `t-rag-m2-05` | `cpn-rag-m2` | Semantic Search — Introduction | 5 | live | tutor |
| `t-rag-m2-06` | `cpn-rag-m2` | Semantic Search — Embedding Model Deep Dive | 6 | live | tutor |
| `t-rag-m2-07` | `cpn-rag-m2` | Vector Embeddings in RAG | 7 | live | tutor |
| `t-rag-m2-08` | `cpn-rag-m2` | Hybrid Search | 8 | live | tutor |
| `t-rag-m2-09` | `cpn-rag-m2` | Evaluating Retrieval | 9 | live | tutor |
| `t-rag-m2-10` | `cpn-rag-m2` | Retrieval Metrics | 10 | live | tutor |

#### `topic_contents` — Topic "Metadata Filtering" (1 per type)
| id | topic_id | content_type | title | order | extraction_status |
|---|---|---|---|---|---|
| `tc-m2-mf-vid` | `t-rag-m2-02` | video | Metadata Filtering (lecture) | 1 | skipped |
| `tc-m2-mf-txt` | `t-rag-m2-02` | text | Metadata Filtering (notebook transcript) | 2 | complete |

#### `exam_templates` — Module 2 quiz
| id | course_path_node_id | topic_id | title | purpose | mode | created_by |
|---|---|---|---|---|---|---|
| `et-rag-m2-quiz` | `cpn-rag-m2` | NULL | Module 2 Quiz | quiz | static | `zain_sub` |

> `topic_id = NULL` because the quiz spans the whole module (all topics in `cpn-rag-m2`), not a single topic.

---

### Example 2 — DeepLearning.AI MCP Course (flat, 1-level)

No module layer. Topics hang directly off the `course` node.

```
CoursePathNode (course): "MCP: Build Rich-Context AI Apps with Anthropic"  ← leaf node
  └── Topic: "Introduction"
  └── Topic: "Why MCP"
  └── Topic: "MCP Architecture"
  └── Topic: "Chatbot Example"
  └── Topic: "Creating an MCP Server"
  └── Topic: "Creating an MCP Client"
  └── Topic: "Connecting MCP Chatbot to Reference Servers"
  └── Topic: "Adding Prompt and Resource Features"
  └── Topic: "Configuring Servers for Claude Desktop"
  └── Topic: "Creating and Deploying Remote Servers"
  └── Topic: "Conclusion"
```

#### `course_path_nodes`
| id | parent_id | name | node_type | owner_type |
|---|---|---|---|---|
| `cpn-mcp` | NULL | MCP: Build Rich-Context AI Apps with Anthropic | course | tutor |

#### `topics`
| id | course_path_node_id | title | order |
|---|---|---|---|
| `t-mcp-01` | `cpn-mcp` | Introduction | 1 |
| `t-mcp-02` | `cpn-mcp` | Why MCP | 2 |
| `t-mcp-03` | `cpn-mcp` | MCP Architecture | 3 |
| `t-mcp-04` | `cpn-mcp` | Chatbot Example | 4 |
| `t-mcp-05` | `cpn-mcp` | Creating an MCP Server | 5 |
| `t-mcp-06` | `cpn-mcp` | Creating an MCP Client | 6 |
| `t-mcp-07` | `cpn-mcp` | Connecting MCP Chatbot to Reference Servers | 7 |
| `t-mcp-08` | `cpn-mcp` | Adding Prompt and Resource Features | 8 |
| `t-mcp-09` | `cpn-mcp` | Configuring Servers for Claude Desktop | 9 |
| `t-mcp-10` | `cpn-mcp` | Creating and Deploying Remote Servers | 10 |
| `t-mcp-11` | `cpn-mcp` | Conclusion | 11 |

#### `topic_contents` — Topic "MCP Architecture"
| id | topic_id | content_type | title | order | extraction_status |
|---|---|---|---|---|---|
| `tc-mcp-03-vid` | `t-mcp-03` | video | MCP Architecture (14 min) | 1 | skipped |
| `tc-mcp-03-txt` | `t-mcp-03` | text | Architecture code walkthrough | 2 | complete |

---

### Example 3 — Coursera Enterprise Architecture (week-based, 2-level)

```
CoursePathNode (course): "Enterprise Architecture"
  └── CoursePathNode (week): "Week 1 — Introduction to EA Frameworks"   ← leaf node
        └── Topic: "What is Enterprise Architecture?"
        └── Topic: "Why EA Matters"
        └── Topic: "Overview of EA Frameworks"
  └── CoursePathNode (week): "Week 2 — TOGAF and ADM"
        └── Topic: "TOGAF Overview"
        └── Topic: "The Architecture Development Method"
        └── Topic: "ADM Phases in Practice"
  └── CoursePathNode (week): "Week 3 — Business and Information Architecture"
        └── Topic: "Business Architecture Overview"
        └── Topic: "Information Architecture"
        └── Topic: "Mapping Business to IT"
  └── CoursePathNode (week): "Week 4 — Technology Architecture and Governance"
        └── Topic: "Technology Architecture Patterns"
        └── Topic: "EA Governance"
        └── Topic: "Putting It All Together"
```

#### `topic_contents` — Topic "TOGAF Overview" (reading + video)
| id | topic_id | content_type | title | order | extraction_status |
|---|---|---|---|---|---|
| `tc-ea-tog-vid` | `t-ea-w2-01` | video | TOGAF Overview (lecture) | 1 | skipped |
| `tc-ea-tog-pdf` | `t-ea-w2-01` | pdf | TOGAF Reference Reading | 2 | complete |

---

### Example 4 — Udemy Learn Kubernetes (section-based, 2-level)

```
CoursePathNode (course): "Learn Kubernetes"
  └── CoursePathNode (section): "Introduction"                          ← leaf node
        └── Topic: "Course Introduction"
        └── Topic: "Setup and Tools"
  └── CoursePathNode (section): "Kubernetes Overview"
        └── Topic: "What is Kubernetes?"
        └── Topic: "Kubernetes Architecture"
        └── Topic: "Containers and Docker Recap"
  └── CoursePathNode (section): "PODs, ReplicaSets, Deployments"
        └── Topic: "PODs with YAML"
        └── Topic: "ReplicaSets"
        └── Topic: "Deployments"
  └── CoursePathNode (section): "Networking in Kubernetes"
        └── Topic: "Cluster Networking Basics"
        └── Topic: "DNS in Kubernetes"
  └── CoursePathNode (section): "Services"
        └── Topic: "NodePort"
        └── Topic: "ClusterIP"
        └── Topic: "LoadBalancer"
  └── CoursePathNode (section): "Microservices Architecture"
        └── Topic: "Designing Microservices on Kubernetes"
        └── Topic: "Deploying a Sample Application"
  └── ... (more sections)
```

#### `topic_contents` — Topic "PODs with YAML" (video + PDF reference)
| id | topic_id | content_type | title | order | extraction_status |
|---|---|---|---|---|---|
| `tc-k8s-pods-vid` | `t-k8s-pods` | video | PODs with YAML (lecture) | 1 | skipped |
| `tc-k8s-pods-pdf` | `t-k8s-pods` | pdf | PODs YAML reference sheet | 2 | complete |

---

## Node Type Summary — Who Uses What

| Owner | Track | Tree shape | node_type values |
|---|---|---|---|
| NCERT (platform admin) | Structured | grade → subject → chapter | `grade`, `subject`, `chapter` |
| CBSE / ICSE (platform admin) | Structured | grade → subject → chapter | `grade`, `subject`, `chapter` |
| Cambridge IGCSE (platform admin) | Structured | grade → subject → unit | `grade`, `subject`, `unit` |
| IB MYP (platform admin) | Structured | grade → subject_group → subject → unit | `grade`, `subject_group`, `subject`, `unit` |
| St. Mary's (institution admin) | Structured (adopted) | Cloned from board | Same as board, `owner_type = institution` |
| DeepLearning.AI RAG (tutor) | Open | course → module | `course`, `module` |
| DeepLearning.AI MCP (tutor) | Open | course (flat) | `course` |
| Coursera EA (tutor) | Open | course → week | `course`, `week` |
| Udemy Kubernetes (tutor) | Open | course → section | `course`, `section` |
| Ravi — Vedic Maths (tutor) | Open | course (flat) | `course` |

**The system does not care what the label is.** Topics always attach to the leaf node. Only `grade` and `subject` have reserved system behaviour.
