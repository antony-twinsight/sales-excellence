export type Role = "sales_agent" | "sales_manager" | "admin";
export type AppraisalStatus = "pending" | "won" | "lost";

export type Agent = {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  office: string;
  years_experience: number;
  target_market: string;
};

export type Metrics = {
  appraisal_count: number;
  listing_count: number;
  conversion_rate: number;
  average_follow_up_delay: number;
  average_vendor_risk_score: number;
};

export type Appraisal = {
  id: number;
  lead_id: number;
  agent_id: number;
  scheduled_at: string;
  status: AppraisalStatus;
  notes: string;
  vendor_objections: string;
  competitor_agents: string;
  estimated_price: number;
  probability_of_winning: number;
  next_action: string;
  next_action_due: string | null;
  follow_up_delay_hours: number;
  vendor_risk_score: number;
  lead: {
    id: number;
    source: string;
    status: string;
    priority: string;
    vendor: {
      name: string;
      motivation: string;
      risk_profile: string;
    };
    property: {
      address: string;
      suburb: string;
      property_type: string;
      bedrooms: number;
      bathrooms: number;
      parking: number;
      estimated_value: number;
      notes: string;
    };
  };
  agent: Agent;
};

export type Dashboard = {
  user: Agent;
  metrics: Metrics;
  upcoming_appraisals: Appraisal[];
  recent_appraisals: Appraisal[];
};

export type LeadOption = {
  id: number;
  vendor: string;
  property: string;
  source: string;
  status: string;
  priority: string;
};

export type PlaybookExample = {
  id: number;
  title: string;
  category: string;
  behaviour: string;
  script: string;
  decision_pattern: string;
  expected_impact: string;
};

export type Benchmark = {
  agent: Agent;
  metrics: Metrics;
  attributes: Array<{
    attribute_name: string;
    score: number;
    benchmark_score: number;
  }>;
};
