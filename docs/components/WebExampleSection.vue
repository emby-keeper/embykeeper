<script setup>
import { withBase } from 'vitepress';
</script>

<template>
  <div class="web-example-section">
    <div class="content-wrapper">
      <div class="text-content">
        <h2 class="title">在线管理</h2>
        <h3 class="subtitle">支持云部署</h3>
      </div>
      <div class="web-wrapper">
        <img class="web-box" :src="withBase('/web_example.png')" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.web-example-section {
  padding-top: 35px;
  border-radius: 12px;
  background-color: var(--vp-c-bg-soft);
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  width: 100%;
}

.text-content {
  flex: 0 1 auto;
  text-align: center;
  margin-bottom: 2rem;
}

.title {
  margin-top: 0;
  padding-top: 0;
  font-size: 2rem;
  color: var(--vp-c-text-1);
  margin-bottom: 1rem;
  border: none;
}

.subtitle {
  font-size: 1.25rem;
  color: var(--vp-c-text-2);
  font-weight: normal;
}

.web-wrapper {
  flex: 1 1 auto;
  width: 100%;
}

.web-box {
  border-radius: 8px;
  box-shadow: 0 0 30px 12px rgba(100, 149, 237, 0.3);
  pointer-events: none;
}

.dark .web-box {
  box-shadow: 0 0 15px 5px rgba(100, 149, 237, 0.2);
}

@media (min-width: 960px) {
  .web-example-section {
    padding: 4rem 4rem;
  }

  .content-wrapper {
    flex-direction: row;
  }

  .text-content {
    flex: 1 1 auto;
    flex-basis: 25%;
    text-align: left;
    margin-bottom: 0;
    margin-top: 5rem;
  }

  .title {
    font-size: 2.5rem;
  }

  .subtitle {
    font-size: 1.5rem;
  }

  .web-wrapper {
    flex: 1 1 auto;
    flex-basis: 75%;
  }
}
</style>
