<template>
  <BaseNode v-bind="props" type="playbook" />
</template>

<script setup>
import BaseNode from './BaseNode.vue'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})
</script>
