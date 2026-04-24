<template>
  <BaseNode v-bind="props" type="parallel" />
</template>

<script setup>
import BaseNode from './BaseNode.vue'

const props = defineProps({
  id: String,
  data: Object,
  selected: Boolean
})
</script>
