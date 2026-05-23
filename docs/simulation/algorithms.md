# Simulation Algorithms

目前 `src.simulation.registry` 註冊三個演算法：

- `time_averaged_random_cancellation`
- `event_balanced`
- `best_size_changed`

它們都輸出相同的 `SimulationResult` schema，差別只在虛擬掛單何時送出與何時重設。
