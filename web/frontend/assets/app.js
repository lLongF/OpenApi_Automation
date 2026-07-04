const { createApp } = Vue;

createApp({
  data() {
    return {
      tab: "run",
      healthText: "服务连接中",
      envs: [],
      modules: [],
      runs: [],
      selectedEnv: "dev",
      selectedModule: "",
      marker: "",
      live: true,
      activeRun: null,
      log: "",
      timer: null,
      currentModule: null,
      selectedCase: null,
      caseJson: "",
      saveMessage: "",
    };
  },
  computed: {
    running() {
      return this.activeRun && ["queued", "running"].includes(this.activeRun.status);
    },
  },
  async mounted() {
    await this.reloadAll();
  },
  methods: {
    async api(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || response.statusText);
      }
      return response.json();
    },
    async reloadAll() {
      await Promise.all([this.reloadHealth(), this.reloadEnvs(), this.reloadCases(), this.reloadRuns()]);
    },
    async reloadHealth() {
      try {
        await this.api("/api/health");
        this.healthText = "FastAPI 已连接";
      } catch (error) {
        this.healthText = "服务不可用";
      }
    },
    async reloadEnvs() {
      const data = await this.api("/api/envs");
      this.envs = data.items || [];
      this.selectedEnv = data.default || this.envs[0]?.name || "dev";
    },
    async reloadCases() {
      const data = await this.api("/api/cases");
      this.modules = data.modules || [];
      if (!this.currentModule && this.modules.length) {
        this.selectModule(this.modules[0].name);
      } else if (this.currentModule) {
        this.selectModule(this.currentModule.name);
      }
    },
    async reloadRuns() {
      const data = await this.api("/api/runs");
      this.runs = data.runs || [];
    },
    async startRun() {
      this.log = "";
      this.activeRun = await this.api("/api/runs", {
        method: "POST",
        body: JSON.stringify({
          env: this.selectedEnv,
          live: this.live,
          marker: this.marker || null,
          module: this.selectedModule || null,
        }),
      });
      this.pollRun();
    },
    async pollRun() {
      clearTimeout(this.timer);
      if (!this.activeRun) return;
      this.activeRun = await this.api(`/api/runs/${this.activeRun.id}`);
      const logData = await this.api(`/api/runs/${this.activeRun.id}/log`);
      this.log = logData.log || "";
      await this.reloadRuns();
      if (this.running) {
        this.timer = setTimeout(() => this.pollRun(), 1500);
      }
    },
    async openRun(run) {
      this.tab = "run";
      this.activeRun = run;
      await this.pollRun();
    },
    selectModule(name) {
      this.currentModule = this.modules.find((item) => item.name === name) || null;
      this.selectedCase = null;
      this.caseJson = "";
      this.saveMessage = "";
    },
    selectCase(item) {
      this.selectedCase = item;
      this.caseJson = JSON.stringify(item, null, 2);
      this.saveMessage = "";
    },
    async saveCase() {
      if (!this.currentModule || !this.selectedCase) return;
      try {
        const parsed = JSON.parse(this.caseJson);
        await this.api(`/api/cases/${this.currentModule.name}/${this.selectedCase.id}`, {
          method: "PUT",
          body: JSON.stringify({ case: parsed }),
        });
        this.saveMessage = "已保存";
        await this.reloadCases();
      } catch (error) {
        this.saveMessage = `保存失败：${error.message}`;
      }
    },
  },
}).mount("#app");
