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
        translations: []
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
        async fetchFilmixData() {
            const response = await axios.post(`${this.currentURL}/api/v1/search`, { name: this.searchQuery, page: this.current_page }, { headers: { "Content-Type": "application/json" } });
            const data = response.data;
            this.current_page = parseInt(data.current_page);
            this.pages = parseInt(data.pages);
            this.content = data.content;
        },
        async fetchTranslations(url) {
          const response = await axios.post(`${this.currentURL}/api/v1/get-translate`, { "url": url }, { headers: { "Content-Type": "application/json" } });
          this.translations = response.data
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
            console.log(name)
            console.log(url)
            console.log(this.selected_filmix_id)
        },
        closeModal() {
            this.showModal = false;
        },
        addToDb() {
            console.log('Adding to DB:', {
                name: this.modalName,
                id: this.selected_filmix_id,
                translation: this.selectedTranslation
            });
            this.closeModal();
        }
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
