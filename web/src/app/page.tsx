import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-green-50 to-white">
      <div className="max-w-6xl mx-auto px-4 py-16">
        <header className="text-center mb-16">
          <h1 className="text-5xl font-bold text-green-800 mb-4">
            Poultry Market Intel
          </h1>
          <p className="text-xl text-green-600 max-w-2xl mx-auto">
            AI-powered intelligence platform for fertilized egg and day-old chick markets.
            Track prices, analyze 3-year trends, detect seasonal effects, and predict futures.
          </p>
        </header>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {[
            { title: "Price Tracking", desc: "Real-time fertilized egg & DOC prices across regions" },
            { title: "Trend Analysis", desc: "3-year historical comparison with seasonal impact detection" },
            { title: "AI Predictions", desc: "Prophet-based forecasting for future price movements" },
          ].map((card) => (
            <div key={card.title} className="bg-white rounded-xl shadow-md p-6 border border-green-100">
              <h2 className="text-xl font-semibold text-green-800 mb-2">{card.title}</h2>
              <p className="text-gray-600">{card.desc}</p>
            </div>
          ))}
        </div>

        <div className="text-center">
          <Link
            href="/dashboard"
            className="inline-block bg-green-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-green-700 transition"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
