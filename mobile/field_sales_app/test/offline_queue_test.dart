import 'package:flutter_test/flutter_test.dart';
import 'package:field_sales_app/models/offline_event.dart';

void main() {
  group('OfflineEvent Model & Serialization Tests', () {
    test('Offline check-in event serializes and deserializes cleanly', () {
      final event = OfflineEvent(
        id: 'ev_123',
        type: 'check_in',
        visitId: 'visit_999',
        payload: {
          'latitude': 12.9716,
          'longitude': 77.5946,
          'accuracy': 12.5,
          'manual_exception_reason': 'Basement parking signal loss',
        },
        createdAt: DateTime.parse('2026-10-22T10:00:00Z'),
        retryCount: 1,
      );

      final jsonStr = event.serialize();
      final restored = OfflineEvent.deserialize(jsonStr);

      expect(restored.id, 'ev_123');
      expect(restored.type, 'check_in');
      expect(restored.visitId, 'visit_999');
      expect(restored.payload['latitude'], 12.9716);
      expect(restored.payload['manual_exception_reason'], 'Basement parking signal loss');
      expect(restored.retryCount, 1);
    });

    test('Offline outcome event round-trip preserves objections and next steps', () {
      final event = OfflineEvent(
        id: 'ev_456',
        type: 'outcome',
        visitId: 'visit_888',
        payload: {
          'status': 'completed',
          'tour_feedback': 'Buyer loved the terrace view',
          'buyer_interest_level': 'high',
          'buyer_objections': ['Price per sqft above budget'],
          'agreed_next_step': 'Send revised payment plan by tomorrow',
        },
        createdAt: DateTime.now(),
      );

      final jsonStr = event.serialize();
      final restored = OfflineEvent.deserialize(jsonStr);

      expect(restored.type, 'outcome');
      expect(restored.payload['status'], 'completed');
      expect(restored.payload['buyer_interest_level'], 'high');
      expect(restored.payload['buyer_objections'], ['Price per sqft above budget']);
    });
  });
}
