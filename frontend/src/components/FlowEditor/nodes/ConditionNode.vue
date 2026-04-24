<template>
  <BaseNode v-bind="props" type="condition" />
</template>

<script setup>
import { markRaw } from 'vue'
import BaseNode from './BaseNode.vue'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})
</script>
