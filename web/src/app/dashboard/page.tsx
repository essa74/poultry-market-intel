export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-3xl font-bold text-green-800 mb-6">Dashboard</h1>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Fertilized Egg Prices</h2>
          <p className="text-gray-500 text-sm">Chart and data table loading...</p>
        </div>
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Day-Old Chick Prices</h2>
          <p className="text-gray-500 text-sm">Chart and data table loading...</p>
        </div>
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">3-Year Trend Comparison</h2>
          <p className="text-gray-500 text-sm">Trend analysis loading...</p>
        </div>
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">AI Price Prediction</h2>
          <p className="text-gray-500 text-sm">Prediction model output loading...</p>
        </div>
      </div>
    </div>
  );
}
