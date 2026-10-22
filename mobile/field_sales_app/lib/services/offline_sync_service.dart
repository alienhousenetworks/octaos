import 'dart:async';
import 'package:field_sales_app/models/offline_event.dart';
import 'package:field_sales_app/services/api_service.dart';
import 'package:field_sales_app/services/storage_service.dart';

class OfflineSyncService {
  final StorageService storage;
  final ApiService api;

  OfflineSyncService(this.storage, this.api);

  List<OfflineEvent> getPendingEvents() {
    final raw = storage.getOfflineQueue();
    return raw.map((str) => OfflineEvent.deserialize(str)).toList();
  }

  Future<void> enqueueEvent({
    required String type,
    required String visitId,
    required Map<String, dynamic> payload,
  }) async {
    final event = OfflineEvent(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      type: type,
      visitId: visitId,
      payload: payload,
      createdAt: DateTime.now(),
    );

    final current = storage.getOfflineQueue();
    current.add(event.serialize());
    await storage.setOfflineQueue(current);
  }

  Future<int> syncPending() async {
    final events = getPendingEvents();
    if (events.isEmpty) return 0;

    final payloadList = events.map((e) => {
      'id': e.id,
      'type': e.type,
      'visit_id': e.visitId,
      ...e.payload,
    }).toList();

    try {
      final res = await api.post('/sales-os/field-sales/sync/offline', {
        'events': payloadList,
      });

      // Clear synced events
      await storage.setOfflineQueue([]);
      return res['synced_count'] ?? events.length;
    } catch (e) {
      // If sync failed, increment retries
      for (var ev in events) {
        ev.retryCount += 1;
      }
      await storage.setOfflineQueue(events.map((e) => e.serialize()).toList());
      rethrow;
    }
  }

  Future<void> clearQueue() async {
    await storage.setOfflineQueue([]);
  }
}
