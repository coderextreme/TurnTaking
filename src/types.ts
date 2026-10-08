export interface Player {
  player_id: string;
  name: string;
  endpoint?: string;
  state: 'active' | 'waiting' | 'skipped' | 'disconnected' | 'eliminated' | 'won';
  score: number;
  moves_left_in_turn: number;
  skipped_rounds: number;
  connected_server_id: string;
  metadata?: Record<string, any>;
  last_heartbeat?: number;
}

export interface Move {
  move_id: string;
  player_id: string;
  action: string;
  payload: Record<string, any>;
  timestamp: number;
  round_number: number;
  contest_id?: string | null;
  server_timestamp?: number;
}

export interface PowerPlay {
  power_play_id: string;
  player_id: string;
  play_type: 'add_moves' | 'take_moves' | 'reverse_order' | 'skip_player' | 'cancel_power_play' | 'swap_order';
  target_player_id?: string | null;
  magnitude: number;
  applied: boolean;
  timestamp: number;
}

export interface Contest {
  contest_id: string;
  contest_type: 'snatch' | 'limited' | 'continuous';
  description: string;
  eligible_player_ids: string[];
  moves_by_player: Record<string, Move[]>;
  max_moves_per_player: number | null;
  time_limit_sec: number | null;
  require_all_players_to_act: boolean;
  start_time: number;
  end_time?: number | null;
  resolved: boolean;
  winner_player_id?: string | null;
  winning_order: string[];
  losing_order: string[];
}

export interface GameState {
  game_id: string;
  progression_type: 'predefined' | 'variable' | 'round_order' | 'snatch' | 'limited' | 'continuous' | 'hybrid';
  round_number: number;
  turn_index: number;
  player_order: string[];
  players: Record<string, Player>;
  active_contest?: Contest | null;
  move_history: Move[];
  power_play_history: PowerPlay[];
  game_over: boolean;
  state_version: number;
  leader_server_id: string;
  updated_at: number;
}

export interface ScenarioResult {
  scenario: string;
  description: string;
  final_state: GameState;
  log: string[];
}

export interface TestResult {
  total_tests: number;
  failures: number;
  errors: number;
  was_successful: boolean;
  duration_sec: number;
  raw_output: string;
  failure_details: string[];
  error_details: string[];
}

export interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileTreeNode[];
}
