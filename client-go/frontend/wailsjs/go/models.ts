export namespace main {
	
	export class ISPInfo {
	    ip: string;
	    isp_name: string;
	    region: string;
	    city: string;
	    asn?: string;
	
	    static createFrom(source: any = {}) {
	        return new ISPInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.ip = source["ip"];
	        this.isp_name = source["isp_name"];
	        this.region = source["region"];
	        this.city = source["city"];
	        this.asn = source["asn"];
	    }
	}
	export class ServiceInfo {
	    id: string;
	    name: string;
	    test_domain: string;
	    blocking_type: string;
	
	    static createFrom(source: any = {}) {
	        return new ServiceInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.test_domain = source["test_domain"];
	        this.blocking_type = source["blocking_type"];
	    }
	}
	export class UpdateInfo {
	    app_update: boolean;
	    app_new_version: string;
	    bin_update: boolean;
	    bin_new_version: string;
	    changelog: string;
	
	    static createFrom(source: any = {}) {
	        return new UpdateInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.app_update = source["app_update"];
	        this.app_new_version = source["app_new_version"];
	        this.bin_update = source["bin_update"];
	        this.bin_new_version = source["bin_new_version"];
	        this.changelog = source["changelog"];
	    }
	}

}

