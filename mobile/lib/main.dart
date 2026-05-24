import 'package:flutter/material.dart';

void main() {
  runApp(const PoultryMarketApp());
}

class PoultryMarketApp extends StatelessWidget {
  const PoultryMarketApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Poultry Market Intel',
      theme: ThemeData(
        colorSchemeSeed: Colors.green,
        useMaterial3: true,
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Poultry Market Intel')),
      body: const Center(
        child: Text('Dashboard — charts and data loading...'),
      ),
    );
  }
}
