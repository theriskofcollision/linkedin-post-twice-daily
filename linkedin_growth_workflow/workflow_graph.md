# LinkedIn Growth Workflow Data Flow

```mermaid
graph TD
    User((User/Hakan)) -->|Trigger/Topic| Orch[Orchestrator]
    
    subgraph Research Phase
        Orch -->|Request Trends| Scout[TrendScout]
        Scout -->|Trend Report| Orch
    end
    
    subgraph Strategy Phase
        Orch -->|Trend Report| Strat[Strategist]
        Strat -->|Strategy Brief (Hook/Angle)| Orch
    end
    
    subgraph Content Creation
        Orch -->|Strategy Brief| Ghost[Ghostwriter]
        Ghost -->|Draft Post| Orch
        
        Orch -->|Strategy Brief| Art[ArtDirector]
        Art -->|Visual Concept| Orch
    end
    
    subgraph Review Phase
        Orch -->|Draft + Visuals| Critic[The Critic]
        Critic -->|Feedback| Orch
        
        Orch -->|Feedback| Ghost
        Orch -->|Feedback| Art
    end
    
    Orch -->|Final Package| User
```
