new Vue({
    el: '#app',
    data: {
        currentURL: `${window.location.protocol}//${window.location.hostname}:${window.location.port}`,
        searchQuery: "",
        current_page: 1,
        pages: 1,
        content: [],
        selected_filmix_id: "",
        showModal: false,
        modalName: "",
        modalLink: "",
        selectedTranslation: "",
        translations: [],
        currentQueueStatus: {},
        currentInProgressStatus: {}
    },
    computed: {
        pagesArray() {
            const pagesArray = [];
            const startPage = Math.max(1, this.current_page - 1);
            const endPage = Math.min(this.pages, this.current_page + 1);

            for (let i = startPage; i <= endPage; i++) {
                pagesArray.push(i);
            }

            return pagesArray;
        }
    },
    mounted() {
        if (this.searchQuery.length > 0) {
            this.fetchFilmixData();
        }
    },
    methods: {
        notifyError(message) {
          this.$snotify.error(message, { timeout: 5000, showProgressBar: true, closeOnClick: true, pauseOnHover: true });
        },
        notifySucess(message) {
          this.$snotify.success(message, { timeout: 5000, showProgressBar: true, closeOnClick: true, pauseOnHover: true });
        },
        notifyInfo(message) {
          this.$snotify.info(message, { timeout: 5000, showProgressBar: true, closeOnClick: true, pauseOnHover: true });
        },
        async fetchFilmixData() {
            const response = await axios.post(`${this.currentURL}/api/v1/search`, { name: this.searchQuery, page: this.current_page }, { headers: { "Content-Type": "application/json" } });
            const data = response.data;
            this.current_page = parseInt(data.current_page);
            this.pages = parseInt(data.pages);
            this.content = data.content;
        },
        async fetchTranslations(url) {
          this.selectedTranslation = ""
          this.translations = []
          const response = await axios.post(`${this.currentURL}/api/v1/get-translate`, { "url": url }, { headers: { "Content-Type": "application/json" } });
          this.translations = response.data
        },
        async getQueue() {
          const response = await axios.post(`${this.currentURL}/api/v1/get-list-queue`, { }, { headers: { "Content-Type": "application/json" } });
          this.currentQueueStatus = response.data.result.queue
          this.currentInProgressStatus = response.data.result.in_progress[0]
        },
        search() {
            this.current_page = 1;
            this.fetchFilmixData();
        },
        changePage(page) {
            if (page >= 1 && page <= this.pages) {
                this.current_page = page;
                this.fetchFilmixData();
            }
        },
        openModal(name, url) {
            this.fetchTranslations(url);
            const regex = /\/([^/]+?)-/;
            const match = url.match(regex);

            if (match && match[1]) {
                this.selected_filmix_id = match[1].split('-')[0];
            } else {
                console.log('ID not found in the URL.');
                this.selected_filmix_id = false;
            }

            this.modalName = name;
            this.modalLink = url;
            this.showModal = true;
        },
        closeModal() {
            this.showModal = false;
        },
        async addToDb() {
          const response = await axios.post(`${this.currentURL}/api/v1/add-to-queue`, { "id": this.selected_filmix_id, "url": this.modalLink, "name": this.modalName, "translation": this.selectedTranslation }, { headers: { "Content-Type": "application/json" } });
          if (response.data.status){
            this.notifySucess(response.data.message)
          } else {
            this.notifyError(response.data.message)
          }
          this.closeModal();
        }
    },
    beforeMount() {
        this.getQueue()
    }
});

// Active link icon
const links = document.querySelectorAll('.nav-link');
const currentPath = window.location.pathname;
links.forEach(link => {
  if (link.getAttribute('href') === currentPath) {
    link.classList.add('active');
  } else {
    link.classList.remove('active');
  }
});

// Spoiler
function toggleSpoiler() {
    const spoiler = document.querySelector('.spoiler');
    const icon = document.querySelector('.spoiler-toggle i');
    spoiler.classList.toggle('open');
    if (spoiler.classList.contains('open')) {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}
