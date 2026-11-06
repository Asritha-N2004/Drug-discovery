export const models = [
  "moving_average",
  "exponential_smoothing",
  "linear_regression",
  "random_forest",
];
export const scenarios: Record<string, string> = {
  online_surge: "Online demand surge",
  store_surge: "Physical store surge",
  warehouse_shortage: "Warehouse shortage",
  supplier_delay: "Supplier delivery delay",
  seasonal_surge: "Seasonal demand surge",
  regional_imbalance: "Regional imbalance",
  promotion_spike: "Promotional sales spike",
};
