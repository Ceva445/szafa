from rest_framework import serializers

class FlexibleInvoiceSerializer(serializers.Serializer):

    items = serializers.ListField(child=serializers.DictField(), required=True)

    def to_internal_value(self, data):
        return data
