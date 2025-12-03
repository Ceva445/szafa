from rest_framework import serializers

class PendingDocumentSerializer(serializers.Serializer):
    document_type = serializers.CharField(required=False)
    document_number = serializers.CharField(required=False)
    items = serializers.ListField(child=serializers.DictField(), required=True)

    def to_internal_value(self, data):
        return data
